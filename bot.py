from threading import Thread
from payment_handler import create_invoice, run_payment_server
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
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

TOKEN = "8128401211:AAG0K7GG23Ia4afmChkaXCct2ULlbP1-8c4"
MASTER_API_KEY = "TmjjxlaUBYl25XFy0A"
MASTER_API_SECRET = "GFZc9MtTs72Plvi1VurxmqiSMv4nL6DV2Axm"

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
            "ru": "📊 Статус",
            "en": "📊 Status"
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
        "menu_support": {
            "ru": "🛟 Поддержка",
            "en": "🛟 Support"
      }
    }
    return texts.get(key, {}).get(lang, texts.get(key, {}).get("ru", ""))

# --- Главное меню ---
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("menu_status", lang), callback_data="status")],
        [InlineKeyboardButton(t("menu_set_amount", lang), callback_data="set_amount")],
        [InlineKeyboardButton(t("menu_support", lang), url="https://t.me/bexruz2281488")]
    ])
    

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_user(user_id):
        save_api_keys(user_id, None, None)
    
    lang_text = (
        "👋 Добро пожаловать в *Bybit Copy Bot*!\n\n"
        "📌 Бот позволяет подключить ваш аккаунт и автоматически копировать сигналы трейдера.\n"
        "⚙️ Введите API-ключ, чтобы начать.\n"
        "📖 Подробная инструкция и описание находятся в нижнем меню.\n\n"
        "👇 Выберите язык:"
    )
    await update.message.reply_text(
        lang_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
        ])
    )

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import ContextTypes
from database import get_user, update_user, get_stats
import logging

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)
    lang = user.get("lang", "ru") if user else "ru"

    # --- Смена языка ---
    if data == "change_language":
        await query.message.reply_text("🌐 Выберите язык / Choose your language:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
        ]))
        return

    elif data.startswith("lang_"):
        lang = "ru" if data == "lang_ru" else "en"
        update_user(user_id, {"lang": lang})
        await query.message.reply_text(
            t("language_set", lang),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📌 Где взять API ключи?", callback_data="how_to_get_api")]
            ])
        )
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    # --- Отправка скриншотов API + переход к вводу ключа ---
    elif data == "how_to_get_api":
        try:
            media = [
                InputMediaPhoto(media=open(f"images/api_{i}.png", "rb")) for i in range(1, 8)
            ]
            await context.bot.send_media_group(chat_id=user_id, media=media)
            update_user(user_id, {"awaiting": "api_key"})
            await context.bot.send_message(chat_id=user_id, text=t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке скринов API: {e}")
            await query.message.reply_text("⚠️ Не удалось отправить изображения.")
        return

    # --- API ключи ---
    elif data == "enter_api" or data == "set_api":
        update_user(user_id, {"awaiting": "api_key"})
        await query.message.reply_text(t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "edit_keys":
        await query.message.reply_text(t("edit_keys", lang), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("replace_keys", lang), callback_data="set_api")],
            [InlineKeyboardButton(t("delete_keys", lang), callback_data="delete_keys")]
        ]))
        return

    elif data == "delete_keys":
        update_user(user_id, {"api_key": None, "api_secret": None, "copy_enabled": False})
        await query.message.reply_text(t("keys_deleted", lang))
        await query.message.reply_text(t("enter_api_key", lang), reply_markup=get_bottom_keyboard(lang))
        update_user(user_id, {"awaiting": "api_key"})
        return

    # --- Статус аккаунта ---
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
        await query.message.reply_text(msg, reply_markup=get_main_menu(lang))
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    # --- Статистика ---
    elif data == "stats":
        stats = get_stats(user_id)
        msg = f"{t('menu_stats', lang)}:\n"
        if not stats:
            msg += t("no_data", lang)
        else:
            for s in stats:
                symbol = s.get("symbol", "N/A")
                side = s.get("side", "N/A")
                qty = s.get("qty", s.get("size", 0))
                price = s.get("price", s.get("entry", 0))
                ts = s.get("timestamp")
                ts_str = ts.strftime("%d.%m %H:%M") if ts else ""
                msg += f"🔹 {symbol} | {side} | {qty} @ {price} {ts_str}\n"
        await query.message.reply_text(msg, reply_markup=get_main_menu(lang))
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    # --- Установить сумму сделки ---
    elif data == "set_amount":
        update_user(user_id, {"awaiting": "fixed_usdt"})
        await query.message.reply_text(t("enter_fixed_amount", lang), reply_markup=get_bottom_keyboard(lang))
        return

    # --- Вкл / Выкл копирование ---
    elif data == "enable_copy":
        if user.get("api_key") and user.get("api_secret"):
            update_user(user_id, {"copy_enabled": True})
            await query.message.reply_text(t("copy_on", lang), reply_markup=get_main_menu(lang))
        else:
            await query.message.reply_text(t("enter_keys_first", lang))
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "disable_copy":
        update_user(user_id, {"copy_enabled": False})
        await query.message.reply_text(t("copy_off", lang), reply_markup=get_main_menu(lang))
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))
        return

    # --- Покупка сигналов ---
    elif data.startswith("buy_"):
        price_map = {
            "buy_10": (10, 10),
            "buy_30": (30, 35),
            "buy_50": (50, 60)
        }
        amount_usd, signals = price_map.get(data, (10, 10))
        payment_url = create_invoice(amount_usd, signals, user_id)
        if payment_url:
            await query.message.reply_text(
                f"✅ Для оплаты *{amount_usd}$* за *{signals}* сигналов, перейдите по ссылке:\n\n{payment_url}",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text("❌ Не удалось создать счет. Повторите попытку позже.")
        return

    # --- Ссылки на описания ---
    elif data == "about_bot":
        url = "https://telegra.ph/Bybit-Signals-Copy-Bot--Opisanie-07-17"
        await query.message.reply_text(f"ℹ️ Подробнее о боте:\n{url}", reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "help_guide":
        url = "https://telegra.ph/Instrukciya-po-ispolzovaniyu-07-17"
        await query.message.reply_text(f"📖 Инструкция:\n{url}", reply_markup=get_bottom_keyboard(lang))
        return

    elif data == "pricing":
        await query.message.reply_text("💳 Тарифы скоро будут добавлены.", reply_markup=get_bottom_keyboard(lang))
        return

    # --- По умолчанию ---
    else:
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_main_menu(lang))
        await query.message.reply_text(t("choose_action", lang), reply_markup=get_bottom_keyboard(lang))

import logging
import requests
from uuid import uuid4
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from pybit.unified_trading import HTTP

from subscribers import add_chat_id
from database import get_user, update_user, save_api_keys

CRYPTOCLOUD_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1dWlkIjoiTmpRek9ETT0iLCJ0eXBlIjoicHJvamVjdCIsInYiOiIzMzY4MmM5N2M4YzkwMTQyNTNlZjgxMTJhYTQwY2M2ZDBhOTkxODUwZjBlODg0OTNmYjNlNjAxMjExMGVkY2Y0IiwiZXhwIjo4ODE1MzExMzAxOX0.pL995r47Mno3rwnaQAA5CZ9NQ7wl4LIqXXzOmFfYrbQ"
CRYPTOCLOUD_SHOP_ID = "pITBUtNlhTsYTDF7"

def get_bottom_keyboard(lang):
    if lang == "ru":
        buttons = [["📖 Инструкция", "ℹ️ О боте"], ["💳 Тарифы", "⚙️ Настройки"]]
    else:
        buttons = [["📖 Instruction", "ℹ️ About"], ["💳 Pricing", "⚙️ Settings"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def create_invoice(amount_usd: float, signals_count: int, user_id: int):
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {
        "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
    "shop_id": CRYPTOCLOUD_SHOP_ID,
    "amount": str(amount_usd),
    "currency": "USD",  # ✅ Указываем USD
    "order_id": f"user{user_id}-{uuid4()}",
    "description": f"Покупка {signals_count} сигналов",
    "custom_fields": {
        "user_id": str(user_id)
    },
    "success_url": "https://t.me/BybitAutoTrader_Bot/successful-payment",
    "fail_url": "https://t.me/BybitAutoTrader_Bot/failed-payment",
    "lifetime": 3600
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["result"]["payment_url"]
    else:
        logging.error(f"❌ Не удалось создать счет: {response.text}")
        return None

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
            [InlineKeyboardButton("10 сигналов - $10", callback_data="buy_10")],
            [InlineKeyboardButton("35 сигналов - $30", callback_data="buy_30")],
            [InlineKeyboardButton("60 сигналов - $50", callback_data="buy_50")]
        ])
        await update.message.reply_text("💳 Выберите тариф:", reply_markup=keyboard)
        return

    if lowered.startswith("buy_"):
        price_map = {"10": (10, 10), "30": (30, 35), "50": (50, 60)}
        key = lowered.split("_")[1]
        amount_usd, signals = price_map.get(key, (10, 10))
        payment_url = create_invoice(amount_usd, signals, user_id)
        if payment_url:
            await update.message.reply_text(
                f"✅ Для оплаты {amount_usd}$ за {signals} сигналов, перейдите по ссылке:\n{payment_url}"
            )
        else:
            await update.message.reply_text("⚠️ Произошла ошибка при создании счета.")
        return

    if lowered in ["⚙️ настройки", "⚙️ settings"]:
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
        await update.message.reply_text(help_text[lang], parse_mode="Markdown", reply_markup=settings_menu(lang))
        return

    await update.message.reply_text(t("choose_action", lang), reply_markup=get_main_menu(lang))

def settings_menu(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Ввести API", callback_data="enter_api")],
        [InlineKeyboardButton("✏️ Редактировать ключи", callback_data="edit_keys")],
        [InlineKeyboardButton("🟢 Включить копирование", callback_data="enable_copy")],
        [InlineKeyboardButton("🔴 Выключить копирование", callback_data="disable_copy")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")],
    ])



import logging
import asyncio
import time
from pybit.unified_trading import HTTP
from trade_executor import open_trade_for_all_clients
from database import get_all_users

MASTER_API_KEY = "TmjjxlaUBYl25XFy0A"
MASTER_API_SECRET = "GFZc9MtTs72Plvi1VurxmqiSMv4nL6DV2Axm"

POLL_INTERVAL = 5  # Проверка каждые 5 секунд
MAX_POSITION_AGE = 600  # ⚠️ 10 минут

already_sent = set()

async def monitor_master_signals(app):
    logging.info("🔄 monitor_master_signals запущен")

    try:
        master = HTTP(api_key=MASTER_API_KEY, api_secret=MASTER_API_SECRET)
        logging.info("🔐 Подключение к Master аккаунту успешно")
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к Master аккаунту: {e}", exc_info=True)
        return

    while True:
        try:
            response = master.get_positions(category="linear", settleCoin="USDT")
            positions = response.get("result", {}).get("list", [])

            logging.debug(f"👁 Получено {len(positions)} позиций от мастера")

            for pos in positions:
                logging.debug(f"🔍 Проверка позиции: {pos}")

                symbol = pos.get("symbol")
                side = pos.get("side")
                size = float(pos.get("size", 0))

                # Подстраховка по entry
                entry_price = float(
                    pos.get("entryPrice") or pos.get("avgPrice") or pos.get("markPrice") or 0
                )

                leverage = float(pos.get("leverage", 1))
                created_time_ms = float(pos.get("createdTime", 0))
                created_time_sec = created_time_ms / 1000

                # ⛔ Фильтрация
                if size <= 0 or entry_price <= 0:
                    logging.debug(f"⏭ Пропущена пустая или нулевая позиция: {symbol}")
                    continue
                if time.time() - created_time_sec > MAX_POSITION_AGE:
                    logging.debug(f"⏳ Пропущена старая позиция: {symbol}")
                    continue

                signal_key = f"{symbol}_{side}_{round(entry_price, 4)}"
                if signal_key in already_sent:
                    logging.debug(f"🔁 Дубликат сигнала: {signal_key}")
                    continue
                already_sent.add(signal_key)

                logging.info(f"[📈 SIGNAL] {symbol} {side} | Entry: {entry_price} | Leverage: {leverage}")

                # Отправка уведомлений
                for user in get_all_users():
                    chat_id = user.get("chat_id")
                    lang = user.get("lang", "ru")
                    if not chat_id:
                        continue

                    msg = (
                        f"{t('new_trade', lang)}\n"
                        f"{t('pair', lang)}: {symbol}\n"
                        f"{t('side', lang)}: {side}\n"
                        f"{t('entry_price', lang)}: {entry_price}\n"
                        f"⚙️ Leverage: {leverage}x"
                    )

                    try:
                        await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                    except Exception as e:
                        logging.warning(f"⚠️ Telegram ошибка: {chat_id} | {e}")

                try:
                    await open_trade_for_all_clients(symbol, side, entry_price, leverage)
                except Exception as e:
                    logging.error(f"[❌ ERROR] Ошибка при открытии сделки: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logging.error(f"[🔥 LOOP ERROR] Ошибка в основном цикле мониторинга: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)

        
import asyncio
import nest_asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Предположим, что у тебя где-то объявлены:
# TOKEN, start, button_handler, handle_text, monitor_master_signals

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
        
    # 🚀 Запуск Flask payment-сервера параллельно
    flask_thread = Thread(target=run_payment_server)
    flask_thread.daemon = True
    flask_thread.start()


    # Обработчики команд и сообщений
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ⏱ Запускаем мониторинг сигналов в фоне
    asyncio.create_task(monitor_master_signals(app))

    print("✅ Бот запущен.")

    # ✅ Новый правильный запуск polling
    await app.run_polling()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())