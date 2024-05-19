import openai
import spacy
from telegram import Update
from telegram.ext import CallbackContext
from pymongo import MongoClient
from config import OPENAI_API_KEY, DB_URI
from chat_utils import save_chat_history

import re
import registration
import logging
openai.api_key = OPENAI_API_KEY

client = MongoClient(DB_URI)
db = client['telegram_bot']
users_collection = db['users']
chat_history_collection = db['chat_history'] 

import logging

nlp_en = spacy.load("en_core_web_sm")
nlp_ru = spacy.load("ru_core_news_sm")

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


async def handle_user_message(update: Update, context: CallbackContext):
    try:
        await save_chat_history(update, context)
        chat_id = update.effective_chat.id
        chat_history = list(db['chat_history'].find({'chat_id': chat_id}))

        messages = [
            {"role": "system", "content": "You are a helpful AI trained to assist with personal development plans."}
        ]

        for message in chat_history[-5:]:
            messages.append({"role": "user" if message['user_id'] != 'bot' else "assistant", "content": message['text']})

        messages.append({"role": "user", "content": update.message.text})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000
        )
        answer = response['choices'][0]['message']['content'].strip()
        await update.message.reply_text(answer)
        await save_chat_history(update, context, answer)

        # Анализ содержимого сообщения на предмет запроса на ментора
        doc = nlp_ru(update.message.text) if 'русский' in update.message.text else nlp_en(update.message.text)
        interests = [token.lemma_ for token in doc if token.pos_ in ['NOUN', 'PROPN']]
        if interests:
            mentors = find_mentors_by_interests(interests)
            if mentors:
                mentor_info = f"Рекомендуем вам ментора: {mentors[0]['name']}, специализация: {mentors[0]['specialization']}."
                await update.message.reply_text(mentor_info)

    except Exception as e:
        logging.error(f"Error handling user message: {str(e)}")
        await update.message.reply_text("Произошла ошибка, пожалуйста, попробуйте еще раз.")

def generate_development_plan(user_data):
    prompt = (f"Создайте план саморазвития для пользователя с следующими данными:\n"
              f"Возраст: {user_data['age']}\n"
              f"Образовательный статус: {user_data['education_status']}\n"
              f"Интересы: {', '.join(user_data['interests'])}\n"
              f"Карьерные цели: {user_data['career_goals']}")
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful AI trained to assist with personal development plans."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']


def find_mentors_by_interests(interests):
    regex_pattern = '|'.join(interests)
    mentors = list(db['users'].find({"role": "mentor", "specialization": {"$regex": regex_pattern, "$options": "i"}}))
    return mentors

async def process_new_user(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = users_collection.find_one({'telegram_id': user_id})

    if user_data:
        development_plan = generate_development_plan(user_data)
        await update.message.reply_text(f"Ваш персонализированный план саморазвития:\n{development_plan}")

        mentors = list(users_collection.find({'role': 'mentor'}))
        mentor = find_mentors_by_interests(user_data['interests'], mentors)
        if mentor:
            mentor_details = f"Ваш ментор: {mentor['name']} ({mentor.get('specialization', 'Не указано')})"
            await update.message.reply_text(mentor_details)
        else:
            await update.message.reply_text("К сожалению, подходящий ментор не найден.")
