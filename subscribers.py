from pymongo import MongoClient

# 🔗 Подключение к MongoDB
MONGO_URI = "mongodb+srv://signalsbybitbot:ByBitSignalsBot%40@cluster0.ucqufe4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)

# 📂 Базы данных и коллекции
db = client["bybit_bot"]
subscribers_collection = db["subscribers"]

signal_db = client["signal_bot"]
users_collection = signal_db["users"]

def add_chat_id(chat_id: int, user_id: int = None):
    """
    Добавляет chat_id в базу, если он еще не подписан.
    Если указан user_id — также связывает с пользователем.
    """
    if not subscribers_collection.find_one({"chat_id": chat_id}):
        subscribers_collection.insert_one({"chat_id": chat_id})

    if user_id:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"chat_id": chat_id}},
            upsert=True
        )

def get_all_chat_ids():
    """
    Возвращает список всех chat_id подписчиков.
    """
    return [doc["chat_id"] for doc in subscribers_collection.find()]

def remove_chat_id(chat_id: int):
    """
    Удаляет chat_id из базы подписчиков.
    """
    subscribers_collection.delete_one({"chat_id": chat_id})
    users_collection.update_many(
        {"chat_id": chat_id},
        {"$unset": {"chat_id": ""}}
    )

def is_subscribed(chat_id: int) -> bool:
    """
    Проверяет, подписан ли chat_id.
    """
    return subscribers_collection.find_one({"chat_id": chat_id}) is not None

def get_user(user_id: int) -> dict:
    """
    Возвращает документ пользователя или создает новый.
    """
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "lang": "ru",
            "awaiting": None
        }
        users_collection.insert_one(user)
    return user

def update_user(user_id: int, data: dict):
    """
    Обновляет поля в документе пользователя.
    """
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )

def save_api_keys(user_id: int, api_key: str, api_secret: str, account_type: str):
    """
    Сохраняет API ключи и тип аккаунта для пользователя.
    """
    users_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "api_key": api_key,
                "api_secret": api_secret,
                "account_type": account_type
            }
        },
        upsert=True
    )
