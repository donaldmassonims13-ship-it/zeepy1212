import requests
from django.conf import settings
from django.utils.html import escape

def send_telegram_message(text: str):
    """
    Отправляет текстовое сообщение во все чаты из settings.TELEGRAM_CHAT_IDS.
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    # Если в settings остался единичный TELEGRAM_CHAT_ID, приведём его к списку:
    chat_ids = getattr(settings, 'TELEGRAM_CHAT_IDS', None)
    if chat_ids is None:
        # fallback на старое поле
        chat_ids = [settings.TELEGRAM_CHAT_ID]
    # Если переменная - строка, а не список, преобразуем ее
    elif isinstance(chat_ids, str):
        chat_ids = [chat_id.strip() for chat_id in chat_ids.split(',')]


    for chat_id in chat_ids:
        # --- НАЧАЛО ИЗМЕНЕНИЙ ---
        payload = {
            'chat_id': str(chat_id),
            'text': text,  # Убрано двойное экранирование escape(text)
            'parse_mode': 'HTML' # Явно указываем режим разметки
        }
        # --- КОНЕЦ ИЗМЕНЕНИЙ ---

        print(f"[TG DEBUG] URL:     {url}")
        print(f"[TG DEBUG] payload: {payload}")
        try:
            r = requests.post(url, data=payload, timeout=5)
            r.raise_for_status()
            print(f"[TG DEBUG] Ответ API (chat {chat_id}): {r.text}")
        except requests.RequestException as e:
            print(f"[TG ERROR] Chat {chat_id}: {e}")

# === Регистрация ===
def notify_registration(user):
    send_telegram_message(
        f"<b>🆕 Новая регистрация!</b>\n"
        f"👤 Email: {escape(user.email)}"
    )
# Алиас
notify_new_user = notify_registration


# === Реф. регистрация ===
def notify_referral_signup(invited_user, inviter):
    send_telegram_message(
        f"<b>👥 Реферальная регистрация</b>\n"
        f"👤 Новый: {escape(invited_user.email)}\n"
        f"🤝 Пригласил: {escape(inviter.email)}"
    )


# === Пополнение баланса (views) ===
def notify_balance_credit(user, amount, source=None):
    msg = (
        f"<b>💰 Пополнение баланса</b>\n"
        f"👤 {escape(user.email)}\n"
        f"💵 Сумма: {amount} $"
    )
    if source:
        msg += f"\n🏷 Источник: {escape(source)}"
    send_telegram_message(msg)


# === Запрос на вывод (views) ===
def notify_withdraw_request(user, amount, method=None, wallet=None):
    msg = (
        f"<b>📤 Запрос на вывод</b>\n"
        f"👤 {escape(user.email)}\n"
        f"💸 Сумма: {amount} $"
    )
    if method:
        msg += f"\n📦 Метод: {escape(method)}"
    if wallet:
        # Кошелек оборачиваем в <pre> и <code>, чтобы сохранить форматирование и символы
        msg += f"\n\n👛 Кошелёк:\n<pre><code>{escape(wallet)}</code></pre>"
    send_telegram_message(msg)


# === Запрос на вывод (admin) ===
def notify_withdrawal_request_admin(req):
    user   = req.user
    date_o = req.created_at
    date   = date_o.strftime('%d.%m.%Y %H:%M') if date_o else '—'
    msg = (
        f"<b>📤 Запрос на вывод (admin)</b>\n"
        f"👤 {escape(user.email)}\n"
        f"💸 Сумма: {req.amount} $\n"
        f"🕓 Дата: {date}\n\n"
        f"👛 Кошелёк:\n<pre><code>{escape(req.wallet_address)}</code></pre>"
    )
    send_telegram_message(msg)
# Алиас для admin.py
notify_withdrawal_request = notify_withdrawal_request_admin


# === Подтверждение вывода ===
def notify_withdrawal_confirmed(req):
    send_telegram_message(
        f"<b>✅ Вывод подтверждён</b>\n"
        f"👤 {escape(req.user.email)}\n"
        f"💵 {req.amount} $"
    )


# === Запрос на пополнение (admin/API) ===
def notify_deposit_request_created(req):
    user   = getattr(req, 'user', None)
    email  = user.email if user else '—'
    wallet = getattr(req, 'wallet_address', '—')
    amo    = getattr(req, 'amount', '—')
    date_o = getattr(req, 'created_at', None)
    date   = date_o.strftime('%d.%m.%Y %H:%M') if date_o else '—'
    send_telegram_message(
        f"<b>🆕 Запрос на пополнение</b>\n"
        f"👤 Email: {email}\n"
        f"💵 Сумма: {amo} $\n"
        f"🕓 Дата: {date}\n\n"
        f"👛 Кошелёк:\n<pre><code>{wallet}</code></pre>"
    )


def notify_deposit_request_confirmed(req):
    user   = getattr(req, 'user', None)
    email  = user.email if user else '—'
    wallet = getattr(req, 'wallet_address', '—')
    amo    = getattr(req, 'amount', '—')
    txid   = getattr(req, 'transaction_id', '—')
    date_o = getattr(req, 'created_at', None)
    date   = date_o.strftime('%d.%m.%Y %H:%M') if date_o else '—'
    send_telegram_message(
        f"<b>💰 Подтверждена заявка на пополнение</b>\n"
        f"👤 Email: {email}\n"
        f"💵 Сумма: {amo} $\n"
        f"🧾 TXID:\n<pre><code>{txid}</code></pre>\n"
        f"👛 Кошелёк:\n<pre><code>{wallet}</code></pre>\n"
        f"🕓 Дата: {date}"
    )


# === Остальные уведомления ===
def notify_buy_request_status_change(user, level_name, status):
    emojis = {'approved': '✅', 'rejected': '❌', 'pending': '🕓'}
    emoji = emojis.get(status, 'ℹ️')
    send_telegram_message(
        f"{emoji} <b>Запрос на покупку уровня обновлён</b>\n"
        f"👤 Пользователь: {escape(user.email)}\n"
        f"📦 Уровень: {escape(level_name)}\n"
        f"📄 Новый статус: {status.capitalize()}"
    )


def notify_admin_level_change(user, new_level):
    send_telegram_message(
        f"<b>🛠️ Изменение уровня вручную</b>\n"
        f"👤 {escape(user.email)}\n"
        f"🎚️ Новый уровень: {new_level}\n"
        f"⚙️ Источник: админка"
    )

def notify_referral_bonus(user, amount, level_from):
    """
    Уведомление о реферальном бонусе:
      user          – User, которому начислен бонус
      amount        – сумма Decimal
      level_from    – номер уровня, от которого пришёл бонус
    """
    send_telegram_message(
        f"<b>💸 Реферальный бонус</b>\n"
        f"👤 {escape(user.email)}\n"
        f"🔗 Уровень: {level_from}\n"
        f"💰 Сумма: {amount} $"
    )
