from flask import Flask, request, jsonify
from pymongo import MongoClient
import logging
import hmac
import hashlib
import requests
from uuid import uuid4

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# MongoDB
MONGO_URI = "mongodb+srv://signalsbybitbot:ByBitSignalsBot%40@cluster0.ucqufe4.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
users_collection = client["signal_bot"]["users"]

# CryptoCloud
SHOP_SECRET = "k6RPc5BOqZVrnwCBa54fep5n0x0GgEtfQqYh"
CRYPTOCLOUD_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1dWlkIjoiTmpRek9ETT0iLCJ0eXBlIjoicHJvamVjdCIsInYiOiIzMzY4MmM5N2M4YzkwMTQyNTNlZjgxMTJhYTQwY2M2ZDBhOTkxODUwZjBlODg0OTNmYjNlNjAxMjExMGVkY2Y0IiwiZXhwIjo4ODE1MzExMzAxOX0.pL995r47Mno3rwnaQAA5CZ9NQ7wl4LIqXXzOmFfYrbQ"
CRYPTOCLOUD_SHOP_ID = "pITBUtNlhTsYTDF7"

# Пакеты сигналов
SIGNAL_PACKAGES = {
    "10": 10,
    "30": 35,
    "50": 60
}

# ✅ Проверка подписи от CryptoCloud
def is_valid_signature(data, signature):
    sorted_items = sorted(data.items())
    message = ':'.join(str(v) for k, v in sorted_items if k != 'sign')
    calculated = hmac.new(SHOP_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return calculated == signature

# 📩 Обработка уведомлений об оплате
@app.route("/payment/notify", methods=["POST"])
def handle_payment_notification():
    data = request.form.to_dict()
    logging.info(f"[PAYMENT NOTIFY] {data}")

    signature = data.get("sign")
    if not is_valid_signature(data, signature):
        logging.warning("❌ Неверная подпись платежа.")
        return jsonify({"error": "Invalid signature"}), 400

    if data.get("status") != "success":
        return jsonify({"status": "ignored"}), 200

    amount = data.get("amount")
    label = data.get("custom_fields[user_id]")
    if not label:
        return jsonify({"error": "Missing user_id"}), 400

    try:
        user_id = int(label)
    except ValueError:
        return jsonify({"error": "Invalid user_id"}), 400

    signals = SIGNAL_PACKAGES.get(str(int(float(amount))))
    if not signals:
        return jsonify({"error": "Unknown amount"}), 400

    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"remaining_signals": signals}},
        upsert=True
    )

    logging.info(f"[✅ SIGNALS ADDED] user_id={user_id}, +{signals}")
    return jsonify({"status": "ok"}), 200

# 🧾 Создание счёта на оплату
def create_invoice(amount_usd: float, signals_count: int, user_id: int):
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {
        "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "shop_id": CRYPTOCLOUD_SHOP_ID,
        "amount": str(amount_usd),
        "currency": "USDT",  # ❗ CryptoCloud требует криптовалюту
        "order_id": f"user{user_id}-{uuid4()}",
        "description": f"Покупка {signals_count} сигналов",
        "custom_fields": {
            "user_id": str(user_id)
        },
        "success_url": "https://t.me/BybitAutoTrader_Bot",  # или свой сайт
        "fail_url": "https://t.me/BybitAutoTrader_Bot",
        "lifetime": 1800
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["result"]["payment_url"]
        else:
            logging.error(f"[❌ CREATE_INVOICE] Ошибка: {response.text}")
            return None
    except Exception as e:
        logging.error(f"[❌ EXCEPTION] Ошибка при создании счёта: {e}")
        return None

# 🚀 Запуск Flask-сервера
def run_payment_server():
    app.run(host="0.0.0.0", port=8888, debug=False)