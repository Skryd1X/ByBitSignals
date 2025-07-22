from pybit.unified_trading import HTTP
from telegram import Bot
from pymongo import MongoClient
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import logging

# --- Telegram Bot ---
BOT_TOKEN = "8128401211:AAG0K7GG23Ia4afmChkaXCct2ULlbP1-8c4"
bot = Bot(token=BOT_TOKEN)

# --- MongoDB ---
MONGO_URI = "mongodb+srv://signalsbybitbot:ByBitSignalsBot%40@cluster0.ucqufe4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
users_collection = client["signal_bot"]["users"]
history_collection = client["signal_bot"]["history"]

# 🔢 Округление по шагу
def round_qty(qty, step):
    return float(Decimal(qty).quantize(Decimal(step), rounding=ROUND_DOWN))

# ✅ Открытие сделки
async def open_trade_for_all_clients(symbol, side, entry_price, leverage, tp=None, sl=None):
    logging.info("📤 Открытие сделок для всех пользователей...")

    for user in users_collection.find({
        "copy_enabled": True,
        "api_key": {"$exists": True, "$ne": None},
        "api_secret": {"$exists": True, "$ne": None}
    }):
        user_id = user["user_id"]
        chat_id = user.get("chat_id")
        fixed_usdt = float(user.get("fixed_usdt", 10))
        signals_left = user.get("signals_left", 0)

        # 🔒 Пропускаем, если сигналов нет
        if signals_left <= 0:
            logging.info(f"[⛔ SKIP] user_id={user_id}, нет доступных сигналов.")
            continue

        try:
            session = HTTP(api_key=user["api_key"], api_secret=user["api_secret"], recv_window=10000)

            # Получаем шаг лота и минимальное кол-во
            info = session.get_instruments_info(category="linear", symbol=symbol)
            info_list = info.get("result", {}).get("list", [])
            if not info_list:
                logging.warning(f"[⚠️ NO INSTRUMENT INFO] user_id={user_id}, symbol={symbol}")
                continue

            lot_info = info_list[0].get("lotSizeFilter", {})
            step = lot_info.get("qtyStep", "0.001")
            min_qty = float(lot_info.get("minOrderQty", step))

            # Расчёт объёма по USDT клиента и плечу мастера
            raw_qty = (fixed_usdt * leverage) / entry_price
            qty = round_qty(raw_qty, step)

            if qty < min_qty:
                logging.warning(f"[⚠️ SKIP] user_id={user_id}, qty={qty} < min={min_qty} for {symbol}")
                continue

            # Позиционный индекс: 1 для Buy, 2 для Sell
            position_idx = 1 if side == "Buy" else 2

            # Пробуем установить плечо
            try:
                session.set_leverage(
                    category="linear",
                    symbol=symbol,
                    buyLeverage=leverage,
                    sellLeverage=leverage
                )
            except Exception as e:
                logging.warning(f"[⚠️ LEVERAGE FAIL] user_id={user_id}, {symbol}: {e}")

            # Сборка ордера
            base_order = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "order_type": "Market",
                "qty": str(qty),
                "time_in_force": "GoodTillCancel",
                "position_idx": position_idx
            }

            if tp:
                base_order["take_profit"] = round(tp, 4)
            if sl:
                base_order["stop_loss"] = round(sl, 4)

            # Удаление не-ASCII символов
            order_clean = {
                k: str(v).encode('ascii', 'ignore').decode() if isinstance(v, str) else v
                for k, v in base_order.items()
            }

            # Подача ордера
            try:
                session.place_order(**order_clean)
            except Exception as e:
                err_text = str(e)
                if "position idx not match position mode" in err_text:
                    logging.warning(f"[⏪ RETRY ORDER] user_id={user_id}, ошибка из-за position_idx. Пробуем без него...")
                    order_clean.pop("position_idx", None)
                    session.place_order(**order_clean)
                else:
                    raise

            # ✅ Списываем сигнал
            users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"signals_left": -1}}
            )

            logging.info(f"[✅ TRADE OPENED] user_id={user_id}, {symbol} {side} qty={qty}")

            history_collection.insert_one({
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "entry": entry_price,
                "size": qty,
                "tp": tp or 0,
                "sl": sl or 0,
                "exit": 0,
                "timestamp": datetime.utcnow()
            })

            if chat_id:
                msg = (
                    f"📈 *Открыта сделка*\n"
                    f"🔹 Пара: {symbol}\n"
                    f"🧭 Сторона: {side}\n"
                    f"🎯 Вход: {entry_price}\n"
                    f"💰 Объём: {qty}\n"
                    f"⚙️ Плечо: {leverage}x"
                )
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"[❌ ERROR] user_id={user_id}: {e}", exc_info=True)

# 🛑 Закрытие сделки
async def close_trade_for_all_clients(symbol: str):
    logging.info("📤 Закрытие сделок...")

    for user in users_collection.find({
        "copy_enabled": True,
        "api_key": {"$exists": True, "$ne": None},
        "api_secret": {"$exists": True, "$ne": None}
    }):
        user_id = user["user_id"]
        chat_id = user.get("chat_id")

        try:
            session = HTTP(api_key=user["api_key"], api_secret=user["api_secret"], recv_window=10000)

            positions = session.get_positions(category="linear", settleCoin="USDT")["result"]["list"]
            position = next((p for p in positions if p["symbol"] == symbol), None)
            if not position or float(position["size"]) == 0:
                continue

            side = "Sell" if position["side"] == "Buy" else "Buy"
            qty = float(position["size"])

            session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                order_type="Market",
                qty=str(qty),
                time_in_force="GoodTillCancel",
                reduce_only=True
            )

            logging.info(f"[🛑 CLOSED] user_id={user_id}, {symbol} qty={qty}")

            history_collection.insert_one({
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "entry": 0,
                "size": qty,
                "tp": 0,
                "sl": 0,
                "exit": 1,
                "timestamp": datetime.utcnow()
            })

            if chat_id:
                msg = (
                    f"🛑 *Сделка закрыта*\n"
                    f"🔹 Пара: {symbol}\n"
                    f"💼 Объём: {qty}\n"
                    f"📅 Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"[❌ CLOSE ERROR] user_id={user_id}: {e}", exc_info=True)
