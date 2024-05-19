from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ConversationHandler,
    MessageHandler, filters, ContextTypes
)
from pymongo import MongoClient
import logging
from mentorship import process_new_user
from chat_utils import save_chat_history

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Подключение к базе данных
client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_bot']
users_collection = db['users']

# Определяем константы состояний
NAME, AGE, ROLE, EDUCATION_STATUS, INTERESTS, CAREER_GOALS, DEVELOPMENT_PREFERENCES, MENTOR_SPECIALIZATION, MENTOR_EXPERIENCE = range(9)

def setup_registration_handlers(application):
    application.add_handler(registration_handler)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context)
    logging.info("Starting registration")
    await update.message.reply_document(document=open('rules&regulations.pdf', 'rb'), caption='Please review the rules and regulations document. By continuing with the registration, you agree to the terms.')
    await update.message.reply_text('Привет! Как тебя зовут?')
    
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context)
    user_name = update.message.text
    context.user_data['name'] = user_name
    logging.info(f"Received name: {user_name}")

    await update.message.reply_text('Сколько тебе лет?')
    
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    user_age = update.message.text
    context.user_data['age'] = user_age
    logging.info(f"Received age: {user_age}")

    keyboard = [
        [InlineKeyboardButton("Пользователь", callback_data='user')],
        [InlineKeyboardButton("Ментор", callback_data='mentor')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выбери свою роль:', reply_markup=reply_markup)
    
    return ROLE

async def role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context)
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data['role'] = role
    logging.info(f"Role selected: {role}")

    if role == 'user':
        await ask_education_status(update, context)
        return EDUCATION_STATUS
    elif role == 'mentor':
        await query.edit_message_text(text='Какая у тебя специализация?')
        return MENTOR_SPECIALIZATION

async def ask_education_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context)
    keyboard = [
        [InlineKeyboardButton("Студент", callback_data='student')],
        [InlineKeyboardButton("Выпускник университета", callback_data='graduate')],
        [InlineKeyboardButton("Школьник", callback_data='school_student')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Выбери свой образовательный статус:', reply_markup=reply_markup)
    
    return EDUCATION_STATUS

async def education_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    query = update.callback_query
    await query.answer()
    education_status = query.data
    context.user_data['education_status'] = education_status
    logging.info(f"Educational status selected: {education_status}")
    await query.edit_message_text(text='Какие у тебя интересы?')
    
    return INTERESTS

async def interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context)
    user_interests = update.message.text
    context.user_data['interests'] = user_interests.split(', ')
    logging.info(f"Received interests: {user_interests}")

    await update.message.reply_text('Каковы твои карьерные цели?')
    
    return CAREER_GOALS

async def career_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    user_career_goals = update.message.text
    context.user_data['career_goals'] = user_career_goals
    logging.info(f"Received career goals: {user_career_goals}")

    await update.message.reply_text('Какие аспекты вашего развития вы хотели бы улучшить?')
    
    return DEVELOPMENT_PREFERENCES

async def development_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    user_preferences = update.message.text
    context.user_data['development_preferences'] = user_preferences
    logging.info(f"Development preferences received: {user_preferences}")

    await update.message.reply_text('Спасибо за регистрацию!')
    await save_user_data(update, context)
    
    return ConversationHandler.END

async def mentor_specialization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    context.user_data['specialization'] = update.message.text
    await update.message.reply_text('Расскажи о своем опыте работы.')
    
    return MENTOR_EXPERIENCE

async def mentor_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await save_chat_history(update, context) 
    context.user_data['experience'] = update.message.text
    await update.message.reply_text('Спасибо за регистрацию как ментор!')
    await save_user_data(update, context)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text('Регистрация была отменена.')
    
    return ConversationHandler.END

async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_id = update.effective_user.id
        username = update.effective_user.username
        user_data = context.user_data
        user_data['username'] = username
        users_collection.update_one({'telegram_id': telegram_id}, {'$set': user_data}, upsert=True)
        await process_new_user(update, context)
        admins = list(users_collection.find({'role': 'admin'}))
        if not admins:
            logging.warning("No admin users found in the database.")
        else:
            new_user_role = user_data.get('role')
            notification_message = f"New {new_user_role}: @{username} (ID: {telegram_id}) has been registered."
            for admin in admins:
                await context.bot.send_message(chat_id=admin['telegram_id'], text=notification_message)
                logging.info(f"Notification sent to admin {admin['username']} successfully.")
    except Exception as e:
        logging.error(f"Failed to save user data or notify admins: {e}")

registration_handler = ConversationHandler(
    entry_points=[CommandHandler('registration', start_registration)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        ROLE: [CallbackQueryHandler(role)],
        EDUCATION_STATUS: [CallbackQueryHandler(education_status)],
        INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, interests)],
        CAREER_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, career_goals)],
        DEVELOPMENT_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, development_preferences)],
        MENTOR_SPECIALIZATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_specialization)],
        MENTOR_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_experience)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
