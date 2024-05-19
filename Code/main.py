from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes, PicklePersistence,
                          ConversationHandler, CallbackContext, MessageHandler, filters)
from config import TOKEN
import registration
import admin
from pymongo import MongoClient
import logging
from mentorship import process_new_user, handle_user_message
from chat_utils import save_chat_history

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_bot']
users_collection = db['users']
chat_history_collection = db['chat_history']

REGISTER, ADMIN_PANEL = range(2)

async def reply_and_save(update: Update, context: CallbackContext, text: str):
    await update.message.reply_text(text)
    context.user_data['should_save_next_outgoing'] = True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_chat_history(update, context)
    telegram_id = update.effective_user.id
    user = users_collection.find_one({'telegram_id': telegram_id})
    logging.debug(f"User with ID {telegram_id} {'found' if user else 'not found'} in the database.")

    if user:
        if user.get('role') == 'admin':
            response_text = 'Привет, администратор! Используй /admin для доступа к админ-панели.'
            next_state = ADMIN_PANEL
        else:
            response_text = f'Привет, {user.get("name")}, рады тебя видеть снова!'
            next_state = ConversationHandler.END
    else:
        response_text = 'Привет! Вам нужно зарегистрироваться, чтобы пользоваться ботом. Введите /registration для начала.'
        next_state = REGISTER

    await update.message.reply_text(response_text)
    await save_chat_history(update, context, response_text)
    return next_state

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 'Unknown user'
    message_text = update.message.text if update.message and update.message.text else 'No message text'
    logging.error(f'Error with message: {message_text} from user {user_id}')
    if update.callback_query:
        await update.callback_query.message.reply_text('Произошла ошибка, давай попробуем начать заново. Введите /start')
    else:
        logging.error('Error occurred but no callback_query or message available to reply to.')

async def handle_admin_message(update: Update, context: CallbackContext):
    if 'target_id' in context.user_data:
        message_text = update.message.text
        message_text = f"От Админстрации бота: {message_text}"
        target_id = context.user_data['target_id']
        target_role = context.user_data.get('target_role', 'user')

        try:
            await context.bot.send_message(chat_id=target_id, text=message_text)
            await update.message.reply_text(f"Сообщение отправлено {'пользователю' if target_role == 'user' else 'ментору'}.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при отправке сообщения: {str(e)}")
        finally:
            context.user_data.pop('target_id', None)
            context.user_data.pop('target_role', None)
    else:
        return None  # Возвращаем None, чтобы обработка сообщения продолжилась следующим обработчиком

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = users_collection.find_one({'telegram_id': user_id})

    if user and user.get('role') == 'admin':
        await handle_admin_message(update, context)
    else:
        await handle_user_message(update, context)

def setup_handlers(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler('start', start))

def setup_mentorship_handlers(application):
    application.add_handler(CommandHandler('mentorship', process_new_user))

def main():
    persistence = PicklePersistence(filepath='bot_persistence')
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    registration.setup_registration_handlers(application)
    admin.setup_admin_handlers(application)
    setup_mentorship_handlers(application)
    setup_handlers(application)
    application.add_error_handler(error_handler)
    application.run_polling()

if __name__ == '__main__':
    main()