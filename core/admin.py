from decimal import Decimal
from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from . import models
# Telegram‑уведомления
from .notifications import (
    notify_new_user,
    notify_referral_signup,
    notify_balance_credit,
    notify_withdraw_request,
    notify_withdrawal_confirmed,
    notify_deposit_request_created,
    notify_deposit_request_confirmed,
    notify_referral_bonus,
    notify_buy_request_status_change,
    notify_admin_level_change,
)




# Регистрируем модели без кастомных классов
admin.site.register(models.DailyReport)
admin.site.register(models.ScooterStats)


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'wallet', 'invited_by')
    # Убрали 'level' — больше не ломает админку
    search_fields = ('user__username', 'wallet')
    list_select_related = ('user', 'invited_by')


    def save_model(self, request, obj, form, change):
        # Смотрим, поменялся ли уровень вручную
        if change and 'level' in form.changed_data:
            old = models.Profile.objects.get(pk=obj.pk)
        super().save_model(request, obj, form, change)
        if change and 'level' in form.changed_data:
            notify_admin_level_change(obj.user, obj.level)


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'amount', 'created_at', 'comment')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'comment')
    list_select_related = ('user',)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        # При создании любой «всё вручную» транзакции-пополнения шлём уведомление
        if is_new and obj.type in ['admin', 'deposit', 'referral']:
            source = obj.type.capitalize()
            if obj.comment:
                source += f' — {obj.comment}'
            notify_balance_credit(obj.user, obj.amount, source=source)


@admin.register(models.ScooterLevel)
class ScooterLevelAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'price', 'income', 'min_daily_profit', 'max_daily_profit',
        'display_photo', 'description',
    )
    list_editable = (
        'price', 'income', 'min_daily_profit', 'max_daily_profit', 'description',
    )
    list_display_links = ('number',)
    ordering = ('number',)

    def display_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="70" height="50" style="object-fit: cover;" />',
                obj.photo.url
            )
        return "Нет фото"
    display_photo.short_description = 'Фото'


def distribute_referral_bonuses(user, deposit_amount):
    """
    Начисляет реферальные бонусы 3‑х уровней и шлёт notify_referral_bonus.
    """
    try:
        profile = models.Profile.objects.select_related('invited_by__profile').get(user=user)
        ref = profile.invited_by
        for lvl, pct in enumerate([Decimal('0.09'), Decimal('0.03'), Decimal('0.01')], start=1):
            if not ref:
                break
            bonus = deposit_amount * pct
            with transaction.atomic():
                ref.profile.balance += bonus
                ref.profile.save()
                models.Transaction.objects.create(
                    user=ref,
                    type='referral',
                    amount=bonus,
                    comment=f'Бонус {pct*100:.0f}% за Level {lvl} (от {user.username})'
                )
            notify_referral_bonus(ref, bonus, lvl)
            ref = ref.profile.invited_by
    except models.Profile.DoesNotExist:
        pass


@admin.register(models.BuyRequest)
class BuyRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'status', 'created_at')
    list_filter = ('status', 'level')
    search_fields = ('user__username',)
    actions = ['approve_selected_requests']

    @admin.action(description='✅ Одобрить выбранные запросы и начислить бонусы')
    def approve_selected_requests(self, request, queryset):
        successful = 0
        for req in queryset.filter(status='pending'):
            user = req.user
            lvl = req.level
            try:
                with transaction.atomic():
                    # 1) создаём/обновляем самокат
                    us, created = models.UserScooter.objects.get_or_create(
                        user=user, level=lvl, defaults={'quantity': 1}
                    )
                    if not created:
                        us.quantity += 1
                        us.save()
                    # 2) списываем за покупку
                    models.Transaction.objects.create(
                        user=user,
                        type='buy',
                        amount=-lvl.price,
                        comment=f"Покупка Level {lvl.number}"
                    )
                    # 3) реферальные бонусы
                    distribute_referral_bonuses(user, lvl.price)
                    # 4) меняем статус и уведомляем
                    req.status = 'approved'
                    req.save()
                    notify_buy_request_status_change(user, lvl.name, 'approved')
                    successful += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Ошибка при обработке запроса {user.username}: {e}",
                    level='error'
                )
        self.message_user(request, f"Успешно одобрено {successful} запросов.")


@admin.register(models.UserScooter)
class UserScooterAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'quantity', 'purchase_date')
    list_filter = ('purchase_date', 'level')
    search_fields = ('user__username',)
    list_editable = ('quantity',)
    list_select_related = ('user', 'level')


@admin.register(models.WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'wallet_address', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'wallet_address')
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            with transaction.atomic():
                if obj.status == 'pending':
                    notify_withdraw_request(obj)
                elif obj.status == 'approved':
                    notify_withdrawal_confirmed(obj)
                    models.Transaction.objects.create(
                        user=obj.user,
                        type='withdraw',
                        amount=-obj.amount,
                        comment=f"Вывод на {obj.wallet_address} подтверждён"
                    )
                elif obj.status == 'rejected':
                    COMM = Decimal('5.00')
                    prof = obj.user.profile
                    prof.balance += obj.amount + COMM
                    prof.save()
                    models.Transaction.objects.create(
                        user=obj.user,
                        type='deposit',
                        amount=obj.amount + COMM,
                        comment="Возврат после отклонения вывода"
                    )
        super().save_model(request, obj, form, change)
