
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from decimal import Decimal
from django.conf import settings

# Профиль пользователя
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    referral_code = models.CharField(max_length=10, unique=True, blank=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_level = models.PositiveIntegerField(default=0)
    last_claim = models.DateTimeField(default=timezone.now)
    wallet = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Telegram Username")


    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:10]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} Profile"


# Транзакции
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Пополнение'),
        ('earning', 'Начисление'),
        ('withdraw', 'Вывод'),
        ('buy', 'Покупка уровня'),
        ('referral', 'Реферальный бонус'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.amount}"



# Уровни самокатов
class ScooterLevel(models.Model):
    number = models.PositiveIntegerField(
        unique=True,
        verbose_name="Номер уровня"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Цена (€)"
    )
    income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Ориентировочный доход в день (€)"
    )
    min_daily_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Мин. дневная прибыль (€)"
    )
    max_daily_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Макс. дневная прибыль (€)"
    )
    expected_scooter_count = models.PositiveIntegerField(
        default=1,
        verbose_name="Кол-во самокатов"
    )

    # ✅ ДОБАВЛЕНЫ ПОЛЯ ДЛЯ ОПИСАНИЯ И ФОТО
    description = models.TextField(
        verbose_name="Описание уровня",
        blank=True,
        help_text="Краткое описание преимуществ этого уровня"
    )
    photo = models.ImageField(
        verbose_name="Фото уровня",
        upload_to='levels/',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Уровень самокатов"
        verbose_name_plural = "Уровни самокатов"
        ordering = ['number']

    def __str__(self):
        return f"Level {self.number}"

    @property
    def roi_days(self):
        if self.income > 0:
            return round(self.price / self.income)
        return None


# Запросы на покупку
class BuyRequest(models.Model):
    """
    Модель для хранения запросов на покупку уровней от пользователей.
    """
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    # ИСПРАВЛЕНО: Указываем правильную модель ScooterLevel
    level = models.ForeignKey(ScooterLevel, on_delete=models.CASCADE, verbose_name="Уровень")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"Запрос от {self.user.username} на Level {self.level.number} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Запрос на покупку"
        verbose_name_plural = "Запросы на покупку"
        ordering = ['-created_at']


class UserScooter(models.Model):
    """
    Модель для связи пользователя с купленным им уровнем самоката.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    level = models.ForeignKey(ScooterLevel, on_delete=models.CASCADE, verbose_name="Уровень самоката")
    # ✅ ДОБАВЛЕНО: Поле для хранения количества самокатов
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата покупки")

    def __str__(self):
        # ✅ ИЗМЕНЕНО: Теперь в названии отображается количество
        return f"{self.user.username} - {self.level} (x{self.quantity})"

    class Meta:
        verbose_name = "Самокат пользователя"
        verbose_name_plural = "Самокаты пользователей"
        # ✅ ИЗМЕНЕНО: Добавлено ограничение для предотвращения дубликатов.
        # Теперь у одного пользователя может быть только ОДНА запись для каждого уровня,
        # а количество меняется в поле 'quantity'.
        unique_together = ('user', 'level')




class WithdrawalRequest(models.Model):
    """
    Модель для хранения запросов на вывод средств от пользователей.
    """
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    wallet_address = models.CharField(max_length=255, verbose_name="Адрес кошелька (USDT TRC-20)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Запрос на вывод от {self.user.username} на сумму ${self.amount}"

    class Meta:
        verbose_name = "Запрос на вывод"
        verbose_name_plural = "Запросы на вывод"
        ordering = ['-created_at']



class DailyReport(models.Model):
    """
    Модель для хранения ежедневных отчетов о прокате.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    report_date = models.DateField(auto_now_add=True, verbose_name="Дата отчета")
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общий пробег (км)")
    profit_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Процент прибыли (%)")
    profit_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма прибыли (€)")
    number_of_trips = models.IntegerField(verbose_name="Количество поездок")

    def __str__(self):
        return f"Отчет для {self.user.username} за {self.report_date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Дневной отчет"
        verbose_name_plural = "Дневные отчеты"
        ordering = ['-report_date'] 
        unique_together = ('user', 'report_date')


from decimal import Decimal

class ScooterStats(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Пользователь"
    )
    report_date = models.DateField(
        default=timezone.now, # Use default instead of auto_now_add
        verbose_name="Дата отчета"
    )
    # Changed from PositiveIntegerField to CharField
    scooter_number = models.CharField(
        max_length=50, 
        verbose_name="Номер самоката"
    )
    # Changed from FloatField to DecimalField for precision
    distance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Пробег (км)"
    )
    trips = models.PositiveIntegerField(
        verbose_name="Количество поездок"
    )
    profit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Прибыль (€)"
    )
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Процент"
    )

    class Meta:
        verbose_name = "Статистика самоката"
        verbose_name_plural = "Статистика самокатов"
        unique_together = ("user", "report_date", "scooter_number")
        ordering = ["-report_date", "scooter_number"]

    def __str__(self):
        return f"{self.user.username} | Скутер {self.scooter_number} | {self.report_date.strftime('%Y-%m-%d')}"

