import random
from decimal import Decimal, ROUND_UP
from .models import ScooterStats, DailyReport
import requests
from django.conf import settings


def generate_scooter_stats(user, total_investment_value, report_date):
    # 🔒 Защита от повторной генерации на ту же дату
    if ScooterStats.objects.filter(user=user, report_date=report_date).exists():
        return

    scooters = user.userscooter_set.all()
    total_distance = 0
    total_profit = Decimal('0.00')
    total_trips = 0

    for scooter in scooters:
        distance = round(random.uniform(22, 55), 2)
        trips = random.randint(6, 23)
        percentage = round(Decimal(random.uniform(2.0, 3.5)), 2)
        profit = Decimal(scooter.level.price) * (percentage / 100)

        # Округляем вверх если > 0.1
        if profit > Decimal('0.1'):
            profit = profit.quantize(Decimal('1.'), rounding=ROUND_UP)

        # Сохраняем в ScooterStats
        ScooterStats.objects.create(
            user=user,
            report_date=report_date,
            scooter_number=scooter.id,
            distance=distance,
            trips=trips,
            profit=profit,
            percentage=percentage
        )

        total_distance += distance
        total_profit += profit
        total_trips += trips

    # Записываем сводный отчет
    DailyReport.objects.update_or_create(
        user=user,
        report_date=report_date,
        defaults={
            'total_distance': total_distance,
            'profit_percentage': (total_profit / total_investment_value * 100) if total_investment_value > 0 else 0,
            'profit_amount': total_profit,
            'number_of_trips': total_trips
        }
    )



def send_telegram_message(message_text: str):
    """
    Отправляет сообщение администратору в Telegram.
    """
    # Получаем токен и ID чата из настроек Django
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)

    if not bot_token or not chat_id:
        print("Ошибка: TELEGRAM_BOT_TOKEN или TELEGRAM_ADMIN_CHAT_ID не настроены в settings.py")
        return

    # URL для запроса к Telegram Bot API
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Параметры запроса
    payload = {
        'chat_id': chat_id,
        'text': message_text,
        'parse_mode': 'HTML'  # Включаем поддержку HTML-тегов, как <b>
    }

    try:
        # Отправляем запрос
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()  # Проверяем, был ли запрос успешным
        print(f"Сообщение в Telegram отправлено: {message_text[:50]}...")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")
