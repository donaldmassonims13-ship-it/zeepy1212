
import telegram
from django.conf import settings
import asyncio

def send_telegram_notification(message: str):
    """
    Отправляет сообщение в Telegram, корректно работая с асинхронной библиотекой
    и проверяя наличие токена.
    """
    # ✅ ДОБАВЛЕНА ПРОВЕРКА: Убеждаемся, что токен и ID чата есть в настройках
    if not all([settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID]):
        print("ОШИБКА: Токен или ID чата для Telegram не указаны в settings.py")
        return

    async def send_async():
        """Вспомогательная асинхронная функция для отправки."""
        try:
            bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            print("Уведомление в Telegram успешно отправлено.")
        except Exception as e:
            print(f"Ошибка при отправке Telegram-уведомления: {e}")

    # Запускаем асинхронную функцию из нашего синхронного кода
    try:
        # Этот способ работает для большинства случаев
        asyncio.run(send_async())
    except RuntimeError:
        # Этот способ нужен, если цикл событий уже запущен (например, в Jupyter или некоторых версиях Django)
        loop = asyncio.get_running_loop()
        loop.create_task(send_async())

