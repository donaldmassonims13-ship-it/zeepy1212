from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Max, F
from datetime import timedelta
import json
import random
from decimal import Decimal
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

# Ваши модели, формы, утилиты
from .models import (
    Profile, Transaction, BuyRequest, UserScooter,
    ScooterLevel, ScooterStats, WithdrawalRequest, DailyReport
)
from .forms import CustomPasswordChangeForm, ProfileUpdateForm
from .utils import generate_scooter_stats



def register(request):
    """Регистрирует пользователя, создаёт профиль и отправляет оповещения в Telegram."""
    ref_code = request.GET.get('ref', '')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        pwd1     = request.POST.get('password1', '')
        pwd2     = request.POST.get('password2', '')
        ref_form = request.POST.get('ref_code', '')

        # 1) Проверка паролей
        if pwd1 != pwd2:
            messages.error(request, 'Пароли не совпадают')
            return redirect(f'/register/?ref={ref_form}')

        # 2) Пользователь существует?
        if User.objects.filter(username=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect(f'/register/?ref={ref_form}')

        # 3) Создаём пользователя
        user = User.objects.create_user(username=email, email=email, password=pwd1)

        # 4) Разруливаем пригласителя
        inviter = None
        if ref_form:
            try:
                inviter = Profile.objects.get(referral_code=ref_form).user
            except Profile.DoesNotExist:
                inviter = None

        # 5) Создаём профиль
        Profile.objects.create(user=user, invited_by=inviter)

        # 6) Отправляем в Telegram
        notify_new_user(user)
        if inviter:
            notify_referral_signup(user, inviter)

        # 7) Уведомляем на сайте и переходим в логин
        messages.success(request, 'Регистрация успешно завершена!')
        return redirect('login')

    # GET — просто отрисуем форму
    return render(request, 'register.html', {'referral_code': ref_code})




def index(request):
    """Сохраняет реферальный код и отображает главную страницу."""
    ref = request.GET.get('ref')
    if ref:
        request.session['ref_code'] = ref
    return render(request, 'index.html')


def login_view(request):
    """Обрабатывает вход пользователя."""
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username',''),
            password=request.POST.get('password','')
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Неверный логин или пароль')
        return redirect('login')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)
    scooters = UserScooter.objects.filter(user=request.user)
    scooters_count = scooters.aggregate(total=Sum('quantity'))['total'] or 0
    highest_level = scooters.aggregate(max_level=Max('level__number'))['max_level'] or 0
    total_earnings = Transaction.objects.filter(
        user=request.user, type='earning'
    ).aggregate(total=Sum('amount'))['total'] or 0
    recent_tx = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    referral_link = request.build_absolute_uri(f'/register/?ref={profile.referral_code}')
    levels = ScooterLevel.objects.all().order_by('number')

    return render(request, 'dashboard.html', {
        'profile': profile,
        'scooters_count': scooters_count,
        'total_earnings': total_earnings,
        'recent_transactions': recent_tx,
        'referral_link': referral_link,
        'levels': levels,
        'highest_level': highest_level,
    })


@login_required
def history(request):
    tx = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'transactions': tx})


def buy_view(request):
    levels = ScooterLevel.objects.all().order_by('number')
    return render(request, 'buy_level.html', {'levels': levels})


def payment_view(request):
    level = get_object_or_404(ScooterLevel, id=request.GET.get('level_id'))
    return render(request, 'payment.html', {'level': level})


@login_required
def finance_view(request):
    tx = Transaction.objects.filter(user=request.user)
    return render(request, 'finance.html', {'transactions': tx})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        if 'wallet' in request.POST:
            profile.wallet = request.POST['wallet']
        profile.save()
        return redirect('profile')

    tx = Transaction.objects.filter(
        user=request.user, type__in=['withdraw','deposit']
    ).order_by('-created_at')
    earnings = Transaction.objects.filter(
        user=request.user, type='earning',
        created_at__gte=timezone.now() - timedelta(days=7)
    )
    earnings_by_day = {}
    for e in earnings:
        d = e.created_at.strftime('%d.%m')
        earnings_by_day[d] = earnings_by_day.get(d, 0) + float(e.amount)

    return render(request, 'profile.html', {
        'profile': profile,
        'transactions': tx,
        'earnings_dates': list(earnings_by_day.keys()),
        'earnings_values': list(earnings_by_day.values()),
    })

@login_required
@csrf_exempt  # убрать по готовности фронта
@require_POST
def create_buy_request(request):
    """
    Создать запрос на покупку уровня и отправить уведомление в Telegram.
    """
    data     = json.loads(request.body)
    level_id = data.get('level_id')
    if not level_id:
        return JsonResponse({'status': 'error', 'message': 'Level ID не указан'}, status=400)

    level = get_object_or_404(ScooterLevel, id=level_id)

    # 1) создаём BuyRequest
    BuyRequest.objects.create(user=request.user, level=level, status='pending')

    # 2) уведомляем в Telegram
    notify_buy_request_status_change(
        request.user,
        f"Level {level.number}",
        'pending'
    )

    # 3) возвращаем ответ
    return JsonResponse({'status': 'success', 'message': 'Запрос успешно создан'})



@login_required
def my_scooters_view(request):
    scooters = UserScooter.objects.filter(user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    last = Transaction.objects.filter(user=request.user, type='earning').order_by('-created_at').first()
    last_ts = last.created_at.isoformat() if last else None
    past = DailyReport.objects.filter(user=request.user)
    highest = scooters.aggregate(max_level=Max('level__number'))['max_level'] or 0
    total_rental = Transaction.objects.filter(user=request.user, type='earning').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'my_scooters.html', {
        'user_scooters': scooters,
        'profile': profile,
        'last_claim_timestamp': last_ts,
        'past_reports': past,
        'highest_level': highest,
        'total_rental_earnings': total_rental,
    })


@login_required
def claim_profit_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Неверный метод запроса'}, status=405)
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    scooters = UserScooter.objects.filter(user=user)
    if not scooters.exists():
        return JsonResponse({'status': 'error', 'message': 'Нет активных самокатов'}, status=400)

    last_tx = Transaction.objects.filter(user=user, type='earning').order_by('-created_at').first()
    if not last_tx:
        tx = Transaction.objects.create(user=user, type='earning', amount=Decimal('0'), comment='Старт')
        return JsonResponse({'status': 'started', 'new_timestamp': tx.created_at.isoformat()})
    elapsed = timezone.now() - last_tx.created_at
    if elapsed < timedelta(seconds=30):
        rem = timedelta(seconds=30) - elapsed
        return JsonResponse({'status': 'error', 'message': f'Ждите {str(rem).split(".")[0]}'}, status=400)

    with transaction.atomic():
        total_inv = scooters.aggregate(total=Sum(F('level__price') * F('quantity')))['total'] or 0
        generate_scooter_stats(user, total_inv, timezone.now().date())
        report = DailyReport.objects.filter(user=user, report_date=timezone.now().date()).order_by('-id').first()
        if not report:
            return JsonResponse({'status': 'error', 'message': 'Отчет не найден'}, status=404)

        profile.balance += report.profit_amount
        profile.total_earned += report.profit_amount
        profile.save()
        new_tx = Transaction.objects.create(
            user=user, type='earning', amount=report.profit_amount,
            comment=f"Доход за {report.number_of_trips} поездок"
        )
        notify_balance_credit(user, report.profit_amount, source='daily_profit')

        stats_qs = ScooterStats.objects.filter(user=user, report_date=report.report_date)
        scooters_data = [{
            'number': s.scooter_number,
            'distance': float(s.distance),
            'trips': s.trips,
            'profit': float(s.profit),
            'percentage': float(s.percentage),
        } for s in stats_qs]

    return JsonResponse({
        'status': 'success',
        'new_balance': float(profile.balance),
        'new_timestamp': new_tx.created_at.isoformat(),
        'report': {
            'date': report.report_date.strftime('%d.%m.%Y'),
            'distance': float(report.total_distance),
            'percentage': float(report.profit_percentage),
            'profit': float(report.profit_amount),
            'trips': report.number_of_trips,
            'scooters': scooters_data,
        }
    })


@login_required
def referral_view(request):
    profile = get_object_or_404(Profile, user=request.user)
    link = request.build_absolute_uri(f'/register/?ref={profile.referral_code}')
    lvl1 = Profile.objects.filter(invited_by=request.user)
    lvl2 = Profile.objects.filter(invited_by__in=[p.user for p in lvl1])
    lvl3 = Profile.objects.filter(invited_by__in=[p.user for p in lvl2])
    ref_earn = Transaction.objects.filter(user=request.user, type='referral').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'referral.html', {
        'referral_link': link,
        'level1_referrals': lvl1,
        'level2_referrals': lvl2,
        'level3_referrals': lvl3,
        'referral_earnings': ref_earn,
        'total_referrals': lvl1.count() + lvl2.count() + lvl3.count(),
    })


@login_required
def settings_view(request):
    pwd_form = CustomPasswordChangeForm(request.user)
    prof_form = ProfileUpdateForm(instance=request.user.profile)
    if request.method == 'POST':
        if 'change_password' in request.POST:
            pwd_form = CustomPasswordChangeForm(request.user, request.POST)
            if pwd_form.is_valid():
                user = pwd_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль обновлён')
                return redirect('settings')
            messages.error(request, 'Ошибки в форме смены пароля')
        elif 'update_profile' in request.POST:
            prof_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
            if prof_form.is_valid():
                prof_form.save()
                messages.success(request, 'Профиль обновлён')
                return redirect('settings')
            messages.error(request, 'Ошибки в форме профиля')

    return render(request, 'settings.html', {'password_form': pwd_form, 'profile_form': prof_form})


def about_view(request):
    return render(request, 'about.html')


@login_required
def create_withdrawal_request(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Неверный метод'}, status=405)

    data = json.loads(request.body)
    # amount — это полная сумма, которую пользователь хочет списать со своего баланса
    try:
        amount = Decimal(str(data.get('amount')))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Неверная сумма'}, status=400)
        
    wallet = data.get('wallet_address')
    profile = get_object_or_404(Profile, user=request.user)
    commission = Decimal('5.00')

    # --- НАЧАЛО ИЗМЕНЕНИЙ ---

    # 1. Валидация
    if not all([amount, wallet]):
        return JsonResponse({'status': 'error', 'message': 'Все поля должны быть заполнены'}, status=400)

    # Проверяем, что на балансе пользователя достаточно средств для списания
    if profile.balance < amount:
        return JsonResponse({'status': 'error', 'message': 'Недостаточно средств на балансе'}, status=400)

    # Проверяем, что запрашиваемая сумма больше комиссии
    if amount <= commission:
        return JsonResponse({'status': 'error', 'message': f'Сумма вывода должна быть больше комиссии (${commission})'}, status=400)
    
    # Проверяем минимальную сумму для списания
    if amount < Decimal('10'):
        return JsonResponse({'status': 'error', 'message': 'Минимальная сумма для вывода $10'}, status=400)

    # Проверяем частоту выводов
    since = timezone.now() - timedelta(hours=12)
    if WithdrawalRequest.objects.filter(user=request.user, created_at__gte=since).exists():
        return JsonResponse({'status': 'error', 'message': 'Вывод можно делать раз в 12 часов'}, status=400)

    # 2. Расчет чистой суммы к получению
    net_amount_to_receive = amount - commission

    # 3. Создаём заявку и списываем средства
    with transaction.atomic():
        # Списываем с баланса полную запрошенную сумму
        profile.balance -= amount
        profile.save()

        # В заявке на вывод указываем чистую сумму, которую получит пользователь
        wr = WithdrawalRequest.objects.create(
            user=request.user,
            amount=net_amount_to_receive,
            wallet_address=wallet,
            status='pending'
        )

    # 4. Уведомляем о чистой сумме вывода
    notify_withdraw_request(request.user, net_amount_to_receive, method='USDT', wallet=wallet)

    # 5. Возвращаем успешный ответ с новым балансом
    return JsonResponse({'status': 'success', 'new_balance': float(profile.balance)})


def generate_scooter_stats(user, total_investment, report_date):
    """
    Генерирует статистику, где прибыль КАЖДОГО самоката находится
    в пределах min/max, заданных в его уровне.
    """
    # Удаляем старую статистику за этот день
    models.ScooterStats.objects.filter(user=user, report_date=report_date).delete()

    # Получаем все самокаты пользователя с их уровнями
    user_scooters_qs = models.UserScooter.objects.select_related('level').filter(user=user)
    if not user_scooters_qs.exists():
        return # Если самокатов нет, выходим

    final_total_distance = Decimal('0.0')
    final_total_trips = 0
    final_total_profit = Decimal('0.0')

    for user_scooter in user_scooters_qs:
        level = user_scooter.level
        
        # Проверяем, что уровень существует, прежде чем его использовать.
        if not level:
            continue # Пропускаем этот самокат и переходим к следующему

        # Проверяем корректность данных уровня
        if level.min_daily_profit <= 0 or level.max_daily_profit <= 0 or level.min_daily_profit >= level.max_daily_profit:
            continue # Пропускаем, если данные о прибыли некорректны

        # Генерируем статистику для каждого экземпляра самоката
        for i in range(user_scooter.quantity):
            min_p = float(level.min_daily_profit)
            max_p = float(level.max_daily_profit)
            scooter_profit = Decimal(str(random.uniform(min_p, max_p)))
            
            scooter_distance = scooter_profit * Decimal(str(random.uniform(1.8, 2.2)))
            scooter_trips = int(scooter_distance / Decimal(str(random.uniform(2.5, 3.5))))
            scooter_percentage = (scooter_profit / level.price) * 100 if level.price > 0 else Decimal('0.0')

            # Создаем запись статистики для конкретного самоката
            models.ScooterStats.objects.create(
                user=user,
                report_date=report_date,
                scooter_number=f"{level.number}-{i+1}",
                distance=scooter_distance.quantize(Decimal("0.01")),
                trips=scooter_trips,
                profit=scooter_profit.quantize(Decimal("0.01")),
                percentage=scooter_percentage.quantize(Decimal("0.01"))
            )

            # Суммируем общие показатели
            final_total_distance += scooter_distance
            final_total_trips += scooter_trips
            final_total_profit += scooter_profit

    # Рассчитываем итоговый процент прибыли
    final_percentage = (final_total_profit / total_investment) * 100 if total_investment > 0 else Decimal('0.0')

    # Создаем или обновляем итоговый дневной отчет
    models.DailyReport.objects.update_or_create(
        user=user,
        report_date=report_date,
        defaults={
            'total_distance': final_total_distance.quantize(Decimal("0.01")),
            'number_of_trips': final_total_trips,
            'profit_amount': final_total_profit.quantize(Decimal("0.01")),
            'profit_percentage': final_percentage.quantize(Decimal("0.01"))
        }
    )




@login_required
def monitoring_view(request):
    count = UserScooter.objects.filter(user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
    return render(request, 'monitoring.html', {'user_scooter_count': count})


def distribute_referral_bonuses(user, deposit_amount):
    try:
        ref = user.profile.invited_by
        for pct in [Decimal('0.09'), Decimal('0.03'), Decimal('0.01')]:
            if not ref:
                break
            bonus = deposit_amount * pct
            with transaction.atomic():
                ref.profile.balance += bonus
                ref.profile.save()
                Transaction.objects.create(
                    user=ref, type='referral', amount=bonus,
                    comment=f'Бонус {pct*100}% от {user.username}'
                )
                notify_balance_credit(ref, bonus, source='referral')
            ref = ref.profile.invited_by
    except Profile.DoesNotExist:
        pass


