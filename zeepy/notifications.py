from .utils import send_telegram_message

def notify_registration(user):
    send_telegram_message(f"🆕 Новая регистрация!\n👤 Email: {user.email}")

def notify_referral_signup(invited_user, inviter):
    send_telegram_message(f"👥 Реферальная регистрация\n👤 {invited_user.email}\n🤝 Пригласил: {inviter.email}")

def notify_deposit(user, amount):
    send_telegram_message(f"💰 Пополнение баланса\n👤 {user.email}\n💵 Сумма: {amount} $")

def notify_withdrawal_request(request_obj):
    user = getattr(request_obj, 'user', None)
    email = getattr(user, 'email', '—')
    telegram = getattr(user, 'telegram_username', '—')  # Или подставь свой путь
    amount = request_obj.amount
    wallet = getattr(request_obj, 'wallet_address', '—')  # Если есть поле
    date = request_obj.created_at.strftime('%d.%m.%Y %H:%M')

    message = (
        f"📤 <b>Новый запрос на вывод</b>\n"
        f"👤 Email: {email}\n"
        f"📲 Telegram: {telegram}\n"
        f"💸 Сумма: {amount} $\n"
        f"🏦 Адрес: {wallet}\n"
        f"🕓 Дата: {date}"
    )
    send_telegram_message(message)

    
def notify_withdrawal_confirmed(request_obj):
    send_telegram_message(f"✅ Вывод подтверждён\n👤 {request_obj.user.email}\n💵 {request_obj.amount} $")

def notify_deposit_request_confirmed(request_obj):
    user = getattr(request_obj, 'user', None)
    email = getattr(user, 'email', '—')
    telegram = request_obj.user_telegram or '—'
    amount = request_obj.amount
    date = request_obj.created_at.strftime('%d.%m.%Y %H:%M')
    txid = request_obj.transaction_id or '—'
    wallet = request_obj.wallet_address or '—'

    message = (
        f"💰 <b>Подтверждено пополнение</b>\n"
        f"👤 Email: {email}\n"
        f"📲 Telegram: {telegram}\n"
        f"💵 Сумма: {amount} $\n"
        f"🏦 Адрес: {wallet}\n"
        f"🧾 Транзакция: {txid}\n"
        f"🕓 Дата: {date}"
    )
    send_telegram_message(message)


def notify_deposit_request_created(request_obj):
    user = getattr(request_obj, 'user', None)
    email = getattr(user, 'email', '—')
    telegram = request_obj.user_telegram or '—'
    amount = request_obj.amount
    date = request_obj.created_at.strftime('%d.%m.%Y %H:%M')
    txid = request_obj.transaction_id or '—'
    wallet = request_obj.wallet_address or '—'

    message = (
        f"🆕 <b>Новый запрос на пополнение</b>\n"
        f"👤 Email: {email}\n"
        f"📲 Telegram: {telegram}\n"
        f"💵 Сумма: {amount} $\n"
        f"🏦 Адрес: {wallet}\n"
        f"🧾 Транзакция: {txid}\n"
        f"🕓 Дата: {date}"
    )
    send_telegram_message(message)



def notify_panel_start(user, level):
    send_telegram_message(f"🚀 Старт панели\n👤 {user.email}\n📦 Уровень: {level.name}")

def notify_panel_claim(user, level, profit):
    send_telegram_message(f"✅ Claim\n👤 {user.email}\n📦 {level.name}\n💸 +{profit} $")

def notify_plan_level_up(user, level):
    send_telegram_message(f"🔼 Новый уровень\n👤 {user.email}\n📦 Уровень: {level}")

def notify_referral_bonus(user, amount, level_from):
    send_telegram_message(f"💸 Реферальный бонус\n👤 {user.email}\n🧬 Уровень: {level_from}\n💰 Сумма: {amount} $")
