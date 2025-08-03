from dotenv import load_dotenv
import os

load_dotenv()
from stats import calculate_full_stats

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

print(f"[DEBUG] CRYPTOBOT_TOKEN={CRYPTOBOT_TOKEN}")

from threading import Thread
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import logging
from database import get_user, save_api_keys, update_user, get_all_users, save_stats, get_stats
from pybit.unified_trading import HTTP
import asyncio
import time

from subscribers import get_all_chat_ids  # ⬅️ ДОБАВЬ ЭТУ СТРОКУ ЗДЕСЬ

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
MASTER_API_KEY = os.getenv("MASTER_API_KEY")
MASTER_API_SECRET = os.getenv("MASTER_API_SECRET")
user_last_order = {}
DEFAULT_RECV_WINDOW = 5000
EXTENDED_RECV_WINDOW = 7500

# Переводы
def t(key, lang):
    texts = {
        "new_trade": {
            "ru": "📈 *Новая сделка от мастера!*",
            "en": "📈 *New trade from master!*"
        },
        "pair": {
            "ru": "🔹 Пара",
            "en": "🔹 Pair"
        },
        "side": {
            "ru": "🧭 Сторона",
            "en": "🧭 Side"
        },
        "volume": {
            "ru": "💰 Объём",
            "en": "💰 Volume"
        },
        "entry_price": {
            "ru": "🎯 Цена входа",
            "en": "🎯 Entry price"
        },
        "menu_enter_api": {
            "ru": "⚙️ Ввести API",
            "en": "⚙️ Enter API"
        },
        "menu_edit_keys": {
            "ru": "✏️ Редактировать ключи",
            "en": "✏️ Edit Keys"
        },
        "menu_status": {
            "ru": "📈 Мой статус",
            "en": "📈 My status"
        },
        "menu_stats": {
            "ru": "📈 Статистика",
            "en": "📈 Statistics"
        },
        "menu_set_amount": {
            "ru": "💵 Установить сумму сделки",
            "en": "💵 Set trade amount"
        },
        "menu_enable": {
            "ru": "🟢 Включить",
            "en": "🟢 Enable"
        },
        "menu_disable": {
            "ru": "🔴 Выключить",
            "en": "🔴 Disable"
        },
        "menu_settings": {
            "ru": "⚙️ Настройки",
            "en": "⚙️ Settings"
        },
        "menu_language": {
            "ru": "🌐 Язык",
            "en": "🌐 Language"
        },
        "welcome": {
            "ru": "👋 Добро пожаловать!",
            "en": "👋 Welcome!"
        },
        "enter_api_key": {
            "ru": "📥 Введите ваш API_KEY:",
            "en": "📥 Enter your API_KEY:"
        },
        "enter_api_secret": {
            "ru": "🔐 Теперь введите API_SECRET:",
            "en": "🔐 Now enter API_SECRET:"
        },
        "edit_keys": {
            "ru": "🔧 Что вы хотите сделать с ключами?",
            "en": "🔧 What would you like to do with keys?"
        },
        "menu_main": {
            "ru": "🏠 Главное меню",
            "en": "🏠 Main menu"
        },
        "replace_keys": {
            "ru": "✏️ Заменить ключи",
            "en": "✏️ Replace keys"
        },
        "delete_keys": {
            "ru": "🗑 Удалить ключи",
            "en": "🗑 Delete keys"
        },
        "keys_deleted": {
            "ru": "🗑 Ключи удалены.",
            "en": "🗑 Keys deleted."
        },
        "keys_missing": {
            "ru": "🔐 Ключи отсутствуют. Введите ключ:",
            "en": "🔐 Keys are missing. Please enter your key:"
        },
        "keys_saved": {
            "ru": "✅ Ключи сохранены! Тип аккаунта",
            "en": "✅ Keys saved! Account type"
        },
        "key_check_error": {
            "ru": "❌ Ошибка при проверке ключей. Убедитесь, что они верны.",
            "en": "❌ Error validating keys. Make sure they are correct."
        },
        "status": {
            "ru": "📊 Статус",
            "en": "📊 Status"
        },
        "status_not_set": {
            "ru": "❌ API ключи не установлены.",
            "en": "❌ API keys not set."
        },
        "copy_enabled": {
            "ru": "🟢 ВКЛ",
            "en": "🟢 ON"
        },
        "copy_disabled": {
            "ru": "🔴 ВЫКЛ",
            "en": "🔴 OFF"
        },
        "copy_on": {
            "ru": "✅ Автокопирование включено.",
            "en": "✅ Copying enabled."
        },
        "copy_off": {
            "ru": "⛔ Автокопирование отключено.",
            "en": "⛔ Copying disabled."
        },
        "enter_fixed_amount": {
            "ru": "Введите сумму в USDT, которую использовать для каждой сделки:",
            "en": "Enter amount in USDT to use for each trade:"
        },
        "usdt_saved": {
            "ru": "Сумма сохранена",
            "en": "Amount saved"
        },
        "enter_positive_usdt": {
            "ru": "Введите положительное число больше 0.",
            "en": "Please enter a positive number greater than 0."
        },
        "invalid_format": {
            "ru": "❌ Неверный формат. Введите число.",
            "en": "❌ Invalid format. Enter a number."
        },
        "enter_keys_first": {
            "ru": "⚠️ Сначала введите API ключи.",
            "en": "⚠️ Please enter API keys first."
        },
        "no_data": {
            "ru": "Нет данных.",
            "en": "No data."
        },
        "account_type": {
            "ru": "Тип аккаунта",
            "en": "Account type"
        },
        "choose_action": {
            "ru": "ℹ️ Выберите действие из меню.",
            "en": "ℹ️ Choose an action from the menu."
        },
        "change_language": {
            "ru": "🌐 Сменить язык",
            "en": "🌐 Change language"
        },
        "order_success": {
            "ru": "✅ Ордер успешно исполнен!",
            "en": "✅ Order executed successfully!"
        },
        "status_hint": {
            "ru": "🔧 Для настройки автокопирования перейдите в настройки",
            "en": "🔧 To configure auto-copying, go to settings"
        },
        "menu_change_lang": {
            "ru": "🌐 Сменить язык",
            "en": "🌐 Change language"
        },
        "language_set": {
            "ru": "✅ Язык установлен: Русский",
            "en": "✅ Language set: English"
        },
        "username_saved": {
            "ru": "Имя пользователя сохранено.",
            "en": "Username saved."
        },
        "menu_balance": {
            "ru": "💰 Баланс сигналов",
            "en": "💰 Signals Balance"
        },
        "buy_signals": {
            "ru": "🛒 Купить сигналы",
            "en": "🛒 Buy signals"
        },
        "menu_back": {
            "ru": "🔙 Назад",
            "en": "🔙 Back"
        },
        "menu_support": {
            "ru": "🛟 Поддержка",
            "en": "🛟 Support"
        }
    }
    return texts.get(key, {}).get(lang, texts.get(key, {}).get("ru", ""))

def get_main_menu(lang):
    texts = {
    "menu_status": {"ru": "📊 Мой статус", "en": "📊 My Status"},
    "menu_stats": {"ru": "📈 Статистика", "en": "📈 Statistics"},  # <--- добавь эту строку
    "menu_balance": {"ru": "💰 Баланс сигналов", "en": "💰 Signal Balance"},
    "buy_signals": {"ru": "🛒 Купить сигналы", "en": "🛒 Buy Signals"},
    "menu_settings": {"ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "menu_support": {"ru": "🆘 Поддержка", "en": "🆘 Support"}
    }
    
    def tr(key):
        return texts.get(key, {}).get(lang, key)

    return InlineKeyboardMarkup([
    [InlineKeyboardButton(tr("menu_status"), callback_data="status")],
    [InlineKeyboardButton(tr("menu_stats"), callback_data="menu_stats")],
    [InlineKeyboardButton(tr("menu_balance"), callback_data="balance")],
    [InlineKeyboardButton(tr("buy_signals"), callback_data="tariff_menu")],
    [InlineKeyboardButton(tr("menu_settings"), callback_data="settings")],
    [InlineKeyboardButton(tr("menu_support"), url="https://t.me/bexruz2281488")]
    ])

    

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_user(user_id):
        save_api_keys(user_id, None, None)

    # 📌 Краткая инструкция (первым сообщением)
    instruction_text = (
        "🚀 ДЛЯ НАЧАЛА РАБОТЫ:\n"
        "1️⃣ ВВЕДИТЕ СВОИ API КЛЮЧИ BYBIT\n"
        "2️⃣ КУПИТЕ СИГНАЛЫ\n"
        "3️⃣ ВКЛЮЧИТЕ АВТОКОПИРОВАНИЕ\n\n"
        "📈 ПОСЛЕ ЭТОГО БОТ НАЧНЁТ ТОРГОВАТЬ ЗА ВАС"
    )
    await update.message.reply_text(instruction_text, parse_mode="Markdown")

    # 👋 Приветственный текст
    welcome_text = (
        "👋 *Добро пожаловать в Bybit Copy Bot!*\n\n"
        "📌 Бот позволяет подключить ваш аккаунт и автоматически копировать сигналы трейдера на бирже Bybit.\n\n"
        "⚠️ *Важно:* Рекомендуется иметь депозит от *100–150 USDT*. "
        "Минимальная сумма одной сделки — *10 USDT* (установлено по умолчанию).\n\n"
        "📉 *Риск-менеджмент:* Рекомендуется использовать не более *5% от депозита* на сделку. "
        "При выборе большей суммы пользователь *несёт полную ответственность* за возможные потери. "
        "Разработчики не несут ответственности за ваши действия и потери.\n\n"
        "📖 Инструкция и описание находятся в нижнем меню.\n\n"
        "👇 Выберите язык:\n\n"
        "––––––––––––––––––––––––––––––––––––––––––\n\n"
        "👋 *Welcome to Bybit Copy Bot!*\n\n"
        "📌 This bot allows you to connect your account and automatically copy trading signals on Bybit.\n\n"
        "⚠️ *Important:* It is recommended to have a deposit of *$100–$150 USDT*. "
        "The minimum trade amount is *$10 USDT* (set by default).\n\n"
        "📉 *Risk management:* It is strongly advised to use no more than *5% of your deposit* per trade. "
        "If you manually select a higher amount, you *accept full responsibility* for any potential losses. "
        "The bot and its developers are *not responsible* for your actions or losses.\n\n"
        "📖 A full guide and description are available in the bottom menu.\n\n"
        "👇 Choose your language:"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
        ])
    )


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient

# Подключение к MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
users_collection = client["signal_bot"]["users"]

async def handle_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    signals_left = user_data.get("signals_left", 0) if user_data else 0
    lang = "ru"  # или получи язык из своей функции, если есть

    if signals_left == 0:
        text_ru = "❗️Вы ещё не приобретали сигналы.\n\nНажмите кнопку ниже, чтобы выбрать тариф и начать копировать сигналы."
        text_en = "❗️You haven't purchased any signals yet.\n\nClick the button below to select a plan and start copying trades."
    else:
        text_ru = f"📊 У вас осталось *{signals_left}* сигналов."
        text_en = f"📊 You have *{signals_left}* signals remaining."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Купить сигналы", callback_data="buy")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ])

    await query.edit_message_text(
        text=text_ru if lang == "ru" else text_en,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user
from cryptobot_payment import create_invoice  # обязательно должен быть импортирован

# 👇 Укажи токен Telegram CryptoBot (полученный у @CryptoBot)
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

# 👇 Тарифы: (кол-во сигналов, цена в USDT)
package_map = {
    "buy_15": (15, 15),
    "buy_30": (35, 30),
    "buy_50": (60, 50),
}

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    tariff = query.data

    if tariff not in package_map:
        await query.edit_message_text("❌ Неверный тариф.")
        return

    signals, amount = package_map[tariff]

    user = get_user(user_id)
    lang = user.get("lang", "ru") if user else "ru"

    # Создание описания и payload для счёта
    description = f"{signals} сигналов за {amount} USDT"
    payload = f"user_{user_id}_{signals}"

    invoice_response = create_invoice(
        amount=amount,
        asset="USDT",
        description=description,
        hidden_payload=payload
    )

    if not invoice_response.get("ok"):
        await query.edit_message_text("⚠️ Ошибка при создании счёта. Попробуйте позже.")
        return

    invoice_url = invoice_response["result"]["pay_url"]

    pay_text = "💳 Оплатить" if lang == "ru" else "💳 Pay"
    back_text = "🔙 Назад" if lang == "ru" else "🔙 Back"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(pay_text, url=invoice_url)],
        [InlineKeyboardButton("🛟 Поддержка" if lang == "ru" else "🛟 Support", url="https://t.me/bexruz2281488")],
        [InlineKeyboardButton(back_text, callback_data="main_menu")]
    ])

    if lang == "ru":
        text = (
            f"📦 Вы выбрали *{signals}* сигналов за *{amount}$*\n\n"
            f"🔐 Оплата через [@CryptoBot](https://t.me/CryptoBot)\n"
            f"✅ Сигналы будут зачислены *автоматически* после оплаты\n\n"
            f"📌 Если возникнут вопросы — [напишите в поддержку](https://t.me/bexruz2281488)"
        )
    else:
        text = (
            f"📦 You selected *{signals}* signals for *{amount}$*\n\n"
            f"🔐 Payment via [@CryptoBot](https://t.me/CryptoBot)\n"
            f"✅ Signals will be credited *automatically* after payment\n\n"
            f"📌 For any issues, [contact support](https://t.me/bexruz2281488)"
        )

    await query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# 💬 Функция отправки сообщения с кнопками (до оплаты)
async def send_invoice_message(context, user_id, amount, signals):
    lang = get_user(user_id).get("lang", "ru")
    callback = "main_menu"

    description = f"{signals} сигналов за {amount} USDT"
    payload = f"user_{user_id}_{signals}"

    invoice_response = create_invoice(
        amount=amount,
        asset="USDT",
        description=description,
        hidden_payload=payload
    )

    if not invoice_response.get("ok"):
        await context.bot.send_message(chat_id=user_id, text="⚠️ Не удалось создать ссылку для оплаты.")
        return

    invoice_url = invoice_response["result"]["pay_url"]

    if lang == "ru":
        text = (
            f"💰 *Счёт на пополнение создан!*\n"
            f"💵 Сумма: *{amount:.2f} USDT*\n\n"
            f"📝 *Инструкция:*\n"
            f"1. Нажмите кнопку «Оплатить» ниже\n"
            f"2. Оплатите встроенным способом Telegram\n"
            f"3. Дождитесь подтверждения транзакции\n\n"
            f"⏳ Счёт действителен *15 минут*\n\n"
            f"✅ После оплаты *{signals} сигналов* будет зачислено на ваш баланс"
        )
        pay_button = "💳 Оплатить"
        back_button = "🔙 Назад"
    else:
        text = (
            f"💰 *Top-up invoice created!*\n"
            f"💵 Amount: *{amount:.2f} USDT*\n\n"
            f"📝 *Instructions:*\n"
            f"1. Click the button below\n"
            f"2. Use Telegram's built-in payment\n"
            f"3. Wait for confirmation\n\n"
            f"⏳ Invoice valid for *15 minutes*\n\n"
            f"✅ After payment, *{signals} signals* will be credited"
        )
        pay_button = "💳 Pay"
        back_button = "🔙 Back"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(pay_button, url=invoice_url)],
        [InlineKeyboardButton(back_button, callback_data=callback)]
    ])

    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import ContextTypes
import logging
from database import get_user, update_user

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)
    lang = user.get("lang", "ru") if user else "ru"

    if not data.startswith("buy_"):
        try:
            await query.message.delete()
        except:
            pass

    if data == "change_language":
        await context.bot.send_message(
            chat_id=user_id,
            text="🌐 Выберите язык / Choose your language:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                 InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
            ])
        )
        return

    elif data.startswith("lang_"):
        lang = "ru" if data == "lang_ru" else "en"
        update_user(user_id, {"lang": lang})
        api_btn = "📌 Где взять API ключи?" if lang == "ru" else "📌 How to get API keys?"
        await context.bot.send_message(
            chat_id=user_id,
            text=t("language_set", lang),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(api_btn, callback_data="how_to_get_api")]
            ])
        )
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "menu_stats":
        stats_text = calculate_full_stats(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        await context.bot.send_message(chat_id=user_id, text=stats_text, parse_mode="Markdown", reply_markup=keyboard)
        return



    elif data == "how_to_get_api":
        try:
            media = [InputMediaPhoto(open(f"images/api_{i}.png", "rb")) for i in range(1, 8)]
            await context.bot.send_media_group(chat_id=user_id, media=media)
            update_user(user_id, {"awaiting": "api_key"})
            await context.bot.send_message(chat_id=user_id, text=t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        except Exception as e:
            logging.error(f"Ошибка отправки изображений API: {e}")
            await context.bot.send_message(chat_id=user_id, text="⚠️ Не удалось отправить изображения.")
        return

    elif data in ("enter_api", "set_api"):
        update_user(user_id, {"awaiting": "api_key"})
        await context.bot.send_message(chat_id=user_id, text=t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "edit_keys":
        await context.bot.send_message(chat_id=user_id, text=t("edit_keys", lang), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("replace_keys", lang), callback_data="set_api")],
        ]))
        return

    elif data == "delete_keys":
        update_user(user_id, {"api_key": None, "api_secret": None, "copy_enabled": False})
        await context.bot.send_message(chat_id=user_id, text=t("keys_deleted", lang))
        await context.bot.send_message(chat_id=user_id, text=t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        update_user(user_id, {"awaiting": "api_key"})
        return

    elif data == "status":
        msg = t("status_not_set", lang)
        if user and user.get("api_key"):
            fixed_usdt = user.get("fixed_usdt", 10)
            msg = (
                f"{t('status', lang)}:\n"
                f"API Key: {user['api_key'][:4]}****\n"
                f"Copying: {t('copy_enabled', lang) if user.get('copy_enabled') else t('copy_disabled', lang)}\n"
                f"Amount: {fixed_usdt} USDT\n"
                f"{t('account_type', lang)}: {user.get('account_type', 'UNIFIED')}"
            )
        await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=get_main_menu(lang))
        await context.bot.send_message(chat_id=user_id, text=t("status_hint", lang))
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "set_amount":
        update_user(user_id, {"awaiting": "fixed_usdt"})
        await context.bot.send_message(chat_id=user_id, text=t("enter_fixed_amount", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "enable_copy":
        if user.get("api_key") and user.get("api_secret"):
            update_user(user_id, {"copy_enabled": True})
            await context.bot.send_message(chat_id=user_id, text=t("copy_on", lang), reply_markup=get_main_menu(lang))
        else:
            await context.bot.send_message(chat_id=user_id, text=t("enter_keys_first", lang))
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "disable_copy":
        update_user(user_id, {"copy_enabled": False})
        await context.bot.send_message(chat_id=user_id, text=t("copy_off", lang), reply_markup=get_main_menu(lang))
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "tariff_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 15 сигналов – 15$", callback_data="buy_15")],
            [InlineKeyboardButton("📦 35 сигналов – 30$", callback_data="buy_30")],
            [InlineKeyboardButton("🚀 60 сигналов – 50$", callback_data="buy_50")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="💼 Выберите пакет сигналов:" if lang == "ru" else "💼 Choose a signal package:",
            reply_markup=keyboard
        )
        return

    elif data == "settings":
        help_text = {
            "ru": (
                "⚙️ *Настройки* — здесь можно:\n\n"
                "🔐 *Ввести API* — подключить свой аккаунт Bybit\n"
                "✏️ *Редактировать ключи* — заменить или удалить ключи\n"
                "🟢 *Включить* — включить автокопирование сигналов\n"
                "🔴 *Выключить* — отключить копирование\n"
                "🌐 *Сменить язык* — переключить язык бота\n\n"
                "👇 Выберите действие:"
            ),
            "en": (
                "⚙️ *Settings* — here you can:\n\n"
                "🔐 *Enter API* — connect your Bybit account\n"
                "✏️ *Edit Keys* — replace or delete keys\n"
                "🟢 *Enable* — turn on signal copying\n"
                "🔴 *Disable* — turn off copying\n"
                "🌐 *Change language* — switch bot language\n\n"
                "👇 Choose an action:"
            )
        }

        await context.bot.send_message(
            chat_id=user_id,
            text=help_text[lang],
            parse_mode="Markdown",
            reply_markup=settings_menu(lang)
        )
        return

    elif data.startswith("buy_"):
        await handle_payment(update, context)
        return

    elif data == "balance":
        signals = user.get("signals_left", 0)
        if signals > 0:
            msg = f"📊 У вас осталось {signals} сигналов." if lang == "ru" else f"📊 You have {signals} signals left."
        else:
            msg = "❗ Вы ещё не приобрели сигналы." if lang == "ru" else "❗ You haven't purchased any signals yet."

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Купить сигналы" if lang == "ru" else "🛒 Buy Signals", callback_data="tariff_menu")],
            [InlineKeyboardButton("🏠 Главное меню" if lang == "ru" else "🏠 Main Menu", callback_data="main_menu")]
        ])
        await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        return

    elif data == "about_bot":
        await context.bot.send_message(
            chat_id=user_id,
            text="ℹ️ Подробнее о боте:\nhttps://telegra.ph/Bybit-Signals-Copy-Bot--Opisanie-07-17",
            reply_markup=get_bottom_keyboard(lang)
        )
        return

    elif data == "help_guide":
        await context.bot.send_message(
            chat_id=user_id,
            text="📖 Инструкция:\nhttps://telegra.ph/Instrukciya-po-ispolzovaniyu-07-17",
            reply_markup=get_bottom_keyboard(lang)
        )
        return

    elif data == "pricing":
        await context.bot.send_message(chat_id=user_id, text="💳 Тарифы скоро будут добавлены.", reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "main_menu":
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_main_menu(lang))
        return

    else:
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_main_menu(lang))
        await context.bot.send_message(chat_id=user_id, text=t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))



import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from pybit.unified_trading import HTTP

from subscribers import add_chat_id
from database import get_user, update_user, save_api_keys


def get_bottom_keyboard(lang):
    if lang == "ru":
        buttons = [["💳 Тарифы", "⚙️ Настройки"], ["📖 Инструкция", "ℹ️ О боте"]]
    else:
        buttons = [["💳 Pricing", "⚙️ Settings"], ["📖 Instruction", "ℹ️ About"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    add_chat_id(chat_id, user_id)

    text = update.message.text.strip()
    lowered = text.lower()
    user = get_user(user_id)
    step = user.get("awaiting")
    lang = user.get("lang", "ru")

    if step == "api_key":
        update_user(user_id, {"api_key": text, "awaiting": "api_secret"})
        await update.message.reply_text(t("enter_api_secret", lang))
        return

    elif step == "api_secret":
        api_key = user["api_key"]
        api_secret = text
        try:
            session = HTTP(api_key=api_key, api_secret=api_secret, recv_window=10000)
            retries = 3
            while retries > 0:
                try:
                    session.get_wallet_balance(accountType="UNIFIED")
                    account_type = "UNIFIED"
                    break
                except Exception as e:
                    if "recv_window" in str(e):
                        session = HTTP(api_key=api_key, api_secret=api_secret, recv_window=10000 + (3 - retries) * 2500)
                        retries -= 1
                    else:
                        raise
            else:
                try:
                    session.get_wallet_balance(accountType="CONTRACT")
                    account_type = "CONTRACT"
                except:
                    raise

            save_api_keys(user_id, api_key, api_secret, account_type)
            update_user(user_id, {"copy_enabled": False, "awaiting": None})
            await update.message.reply_text(
                f"{t('keys_saved', lang)}: {account_type}",
                reply_markup=get_main_menu(lang)
            )
        except Exception as e:
            logging.error(f"Ошибка валидации ключей: {e}")
            await update.message.reply_text(t("key_check_error", lang))
        return

    elif step == "fixed_usdt":
        try:
            amount = float(text)
            if amount > 0:
                update_user(user_id, {"fixed_usdt": amount, "awaiting": None})
                await update.message.reply_text(
                    f"✅ {t('usdt_saved', lang)}: {amount} USDT",
                    reply_markup=get_main_menu(lang)
                )
            else:
                await update.message.reply_text(t("enter_positive_usdt", lang))
        except ValueError:
            await update.message.reply_text(t("invalid_format", lang))
        return

    elif step == "set_username":
        update_user(user_id, {"username": text, "awaiting": None})
        await update.message.reply_text(t("username_saved", lang), reply_markup=get_main_menu(lang))
        return

    elif step == "set_language":
        if text.lower() in ["ru", "en"]:
            update_user(user_id, {"lang": text.lower(), "awaiting": None})
            await update.message.reply_text(t("language_set", text.lower()), reply_markup=get_main_menu(text.lower()))
        else:
            await update.message.reply_text(t("invalid_language", lang))
        return

    if lowered in ["📖 инструкция", "📖 instruction"]:
        await update.message.reply_text("📖 Инструкция:\nhttps://telegra.ph/Instrukciya-po-ispolzovaniyu-07-17")
        return

    if lowered in ["ℹ️ о боте", "ℹ️ about"]:
        await update.message.reply_text("ℹ️ О боте:\nhttps://telegra.ph/Bybit-Signals-Copy-Bot--Opisanie-07-17")
        return

    if lowered in ["💳 тарифы", "💳 pricing"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("15 сигналов - $15", callback_data="buy_15")],
            [InlineKeyboardButton("35 сигналов - $30", callback_data="buy_30")],
            [InlineKeyboardButton("60 сигналов - $50", callback_data="buy_50")]
        ])
        await update.message.reply_text("💳 Выберите тариф:", reply_markup=keyboard)
        return

    if lowered.startswith("buy_"):
        price_map = {"15": (15, 15), "30": (35, 30), "50": (60, 50)} 
        key = lowered.split("_")[1]
        amount_usd, signals = price_map.get(key, (15, 15))
        await send_invoice_message(context, user_id, amount_usd, signals)
        return

    if lowered in ["⚙️ настройки", "⚙️ settings"]:
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("choose_action", lang),
            reply_markup=settings_menu(lang),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(t("choose_action", lang), reply_markup=get_main_menu(lang))


def settings_menu(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("menu_enter_api", lang), callback_data="enter_api")],
        [InlineKeyboardButton(t("menu_edit_keys", lang), callback_data="edit_keys")],
        [InlineKeyboardButton(t("menu_enable", lang), callback_data="enable_copy")],
        [InlineKeyboardButton(t("menu_disable", lang), callback_data="disable_copy")],
        [InlineKeyboardButton(t("menu_set_amount", lang), callback_data="set_amount")],
        [InlineKeyboardButton(t("menu_change_lang", lang), callback_data="change_language")],
        [InlineKeyboardButton(t("menu_main", lang), callback_data="main_menu")]
    ])




import logging
import asyncio
import time
import os
from collections import deque
from pybit.unified_trading import HTTP
from trade_executor import open_trade_for_all_clients, close_trade_for_all_clients
from database import get_all_users

MASTER_API_KEY = "TmjjxlaUBYl25XFy0A"
MASTER_API_SECRET = "GFZc9MtTs72Plvi1VurxmqiSMv4nL6DV2Axm"

POLL_INTERVAL = 5  # каждые 5 секунд
MAX_POSITION_AGE = 900  # максимум 15 минут с момента открытия

already_sent = deque(maxlen=500)

previous_positions = {}

async def monitor_master_signals(app):
    logging.info("🔄 monitor_master_signals запущен")

    try:
        master = HTTP(api_key=MASTER_API_KEY, api_secret=MASTER_API_SECRET)
        logging.info("🔐 Подключение к Master аккаунту успешно")
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к Master аккаунту: {e}", exc_info=True)
        return

    global previous_positions

    while True:
        try:
            response = master.get_positions(category="linear", settleCoin="USDT")
            positions = response.get("result", {}).get("list", [])

            logging.debug(f"📡 Получено {len(positions)} позиций от мастера")

            current_symbols = set()
            for pos in positions:
                symbol = pos.get("symbol")
                side = pos.get("side")
                size = float(pos.get("size", 0))
                entry_price = float(pos.get("entryPrice") or pos.get("avgPrice") or pos.get("markPrice") or 0)
                leverage = float(pos.get("leverage", 1))
                updated_time_ms = float(pos.get("updatedTime", 0))
                signal_time_sec = updated_time_ms / 1000
                now = time.time()
                age = now - signal_time_sec

                logging.debug(
                    f"🔍 {symbol} | side={side} | size={size} | entry={entry_price} | "
                    f"updated_time={updated_time_ms} | age={age:.1f}s"
                )

                if size <= 0:
                    logging.debug(f"⏭ Пропущена нулевая позиция: {symbol}")
                    continue

                if entry_price <= 0:
                    logging.debug(f"⏭ Пропущена позиция без entry_price: {symbol}")
                    continue

                if age > MAX_POSITION_AGE:
                    logging.debug(f"⏳ Пропущена старая позиция: {symbol} (age: {int(age)}s)")
                    continue

                signal_key = f"{symbol}_{side}_{round(entry_price, 4)}_{size}_{int(updated_time_ms)}"
                if signal_key in already_sent:
                    logging.debug(f"🔁 Дубликат сигнала: {signal_key}")
                    current_symbols.add(symbol)
                    continue

                already_sent.append(signal_key)
                logging.info(f"[📈 СИГНАЛ] {symbol} {side} @ {entry_price:.4f} | Leverage: {leverage}x")

                current_symbols.add(symbol)
                previous_positions[symbol] = side

                for user in get_all_users():
                    chat_id = user.get("chat_id")
                    lang = user.get("lang", "ru")
                    signals_left = user.get("signals_left", 0)
                    copy_enabled = user.get("copy_enabled", False)

                    if not chat_id or signals_left <= 0 or not copy_enabled:
                        continue

                    try:
                        msg = (
                            f"{t('new_trade', lang)}\n"
                            f"{t('pair', lang)}: {symbol}\n"
                            f"{t('side', lang)}: {side}\n"
                            f"{t('entry_price', lang)}: {entry_price}\n"
                            f"⚙️ Leverage: {leverage}x"
                        )
                        await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                        logging.info(f"📤 Сигнал отправлен: {chat_id}")
                    except Exception as e:
                        logging.warning(f"⚠️ Telegram ошибка ({chat_id}): {e}")

                try:
                    await open_trade_for_all_clients(symbol, side, entry_price, leverage)
                except Exception as e:
                    logging.error(f"❌ Ошибка в open_trade_for_all_clients: {e}", exc_info=True)

            # 🔻 Проверка на закрытие: если позиция исчезла у мастера — закрыть у всех клиентов
            closed_symbols = set(previous_positions.keys()) - current_symbols
            for closed_symbol in closed_symbols:
                try:
                    logging.info(f"[🛑 ЗАКРЫТИЕ] Мастер закрыл позицию: {closed_symbol}, закрываем у всех клиентов.")
                    await close_trade_for_all_clients(closed_symbol)
                    del previous_positions[closed_symbol]
                except Exception as e:
                    logging.error(f"❌ Ошибка при закрытии позиции {closed_symbol}: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logging.error(f"[🔥 LOOP ERROR] Ошибка в основном цикле: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)




        
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)
import asyncio
import nest_asyncio

# 🔐 Токен бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ✅ Ответ на пречекаут
async def precheckout_callback(update, context):
    await update.pre_checkout_query.answer(ok=True)


# 🔁 Главный запуск
async def main():
    # ✅ Проверка обязательных переменных окружения
    required_vars = ["TELEGRAM_TOKEN", "CRYPTOBOT_TOKEN", "MASTER_API_KEY", "MASTER_API_SECRET", "MONGO_URI"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"⛔ Отсутствуют переменные окружения: {', '.join(missing)}")

    # 🎯 Запуск приложения Telegram
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # 💬 Импорт обработчиков платежей
    from cryptobot_payment import handle_payment, check_invoice_status

    # 💬 Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # ✅ Специфические CallbackQuery — идут ПЕРВЫМИ
    application.add_handler(CallbackQueryHandler(handle_check_balance, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(handle_payment, pattern="^buy_(15|30|50)$"))
    application.add_handler(CallbackQueryHandler(check_invoice_status, pattern="^check_invoice_"))

    # 🔘 Общий обработчик кнопок (в т.ч. настройки)
    application.add_handler(CallbackQueryHandler(button_handler, pattern=".*"))

    # 💬 Обработка текстовых сообщений (нижнее меню)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # 🧠 Фоновый мониторинг сигналов
    asyncio.create_task(monitor_master_signals(application))

    print("✅ Бот запущен.")
    await application.run_polling()
async def wrap_monitor_signals(app):
    try:
        await monitor_master_signals(app)
    except Exception as e:
        logging.error(f"❌ Ошибка в мониторинге сигналов: {e}", exc_info=True)

async def main():
    required_vars = ["TELEGRAM_TOKEN", "CRYPTOBOT_TOKEN", "MASTER_API_KEY", "MASTER_API_SECRET", "MONGO_URI"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"⛔ Отсутствуют переменные окружения: {', '.join(missing)}")

    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    from cryptobot_payment import handle_payment, check_invoice_status
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_check_balance, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(handle_payment, pattern="^buy_(15|30|50)$"))
    application.add_handler(CallbackQueryHandler(check_invoice_status, pattern="^check_invoice_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern=".*"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    asyncio.create_task(wrap_monitor_signals(application))

    logging.info("✅ Бот запущен.")
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    # Безопасный тест
    try:
        from cryptobot_payment import create_invoice
        print(create_invoice(1, "USDT", "Test", "payload_test"))
    except Exception as e:
        logging.warning(f"⚠️ Ошибка при тестовом создании инвойса: {e}")

    asyncio.run(main())


# 🚀 Запуск
if __name__ == "__main__":
    from cryptobot_payment import create_invoice
    print(create_invoice(1, "USDT", "Test", "payload_test"))
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())