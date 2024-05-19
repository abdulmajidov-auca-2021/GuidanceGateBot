# chat_utils.py
import datetime
from pymongo import MongoClient

# Подключение к базе данных
client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_bot']
chat_history_collection = db['chat_history']

async def save_chat_history(update, context, outgoing_text=None):
    """Сохраняет историю чата в базу данных."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 'unknown'
    incoming_text = update.message.text if update.message else 'non-text message'

    # Сохранение входящего сообщения
    if incoming_text:
        chat_history_collection.insert_one({
            'chat_id': chat_id,
            'user_id': user_id,
            'text': incoming_text,
            'date': update.message.date if update.message else datetime.datetime.now()
        })

    # Сохранение исходящего сообщения, если оно есть
    if outgoing_text:
        chat_history_collection.insert_one({
            'chat_id': chat_id,
            'user_id': 'bot',
            'text': outgoing_text,
            'date': datetime.datetime.now()  # Используем текущее время для исходящего сообщения
        })
