from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_bot']
users_collection = db['users']

async def admin_panel(update: Update, context: CallbackContext):
    # Получение информации о пользователе из базы данных
    user = users_collection.find_one({'telegram_id': update.effective_user.id})

    # Проверка, что пользователь имеет роль 'admin'
    if user and user.get('role') == 'admin':
        keyboard = [
            [InlineKeyboardButton("Пользователи", callback_data='view_users')],
            [InlineKeyboardButton("Менторы", callback_data='view_mentors')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите категорию:', reply_markup=reply_markup)
    else:
        # Сообщение для пользователей, которые не являются администраторами
        await update.message.reply_text('У вас нет доступа к этой команде.')

async def view_users(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    users = list(users_collection.find({'role': 'user'}))
    keyboard = [
        [InlineKeyboardButton(user['name'], callback_data=f"user_{user['telegram_id']}")]
        for user in users
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Выберите пользователя:", reply_markup=reply_markup)

async def user_details(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    user = users_collection.find_one({'telegram_id': user_id})
    if user is None:
        await query.edit_message_text(text="Пользователь не найден.")
        return
    details = f"Имя: {user['name']}\nВозраст: {user.get('age', 'Не указано')}\nНикнейм: @{user.get('username', 'Не указано')}\nОбразовательный статус: {user.get('education_status', 'Не указано')}\nИнтересы: {', '.join(user.get('interests', []))}\nКарьерные цели: {user.get('career_goals', 'Не указано')}\nАспекты развития которых хочет развивать: {user.get('development_preferences', 'Не указано')}"
    keyboard = [
        [InlineKeyboardButton("Написать пользователю", callback_data=f"message_user_{user['telegram_id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=details, reply_markup=reply_markup)

async def send_message_to_user(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    target_id = int(query.data.split('_')[2])
    context.user_data['target_id'] = target_id  # Сохраняем ID пользователя для отправки сообщения
    context.user_data['target_role'] = 'user'  # Указываем роль для уточнения логики отправки
    await query.edit_message_text(text="Введите сообщение для пользователя:")

async def view_mentors(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    mentors = list(users_collection.find({'role': 'mentor'}))
    keyboard = [
        [InlineKeyboardButton(mentor['name'], callback_data=f"mentor_{mentor['telegram_id']}")]
        for mentor in mentors
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Выберите ментора:", reply_markup=reply_markup)

async def mentor_details(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    mentor_id = int(query.data.split('_')[1])
    mentor = users_collection.find_one({'telegram_id': mentor_id})
    if mentor is None:
        await query.edit_message_text(text="Ментор не найден.")
        return
    details = f"Имя: {mentor['name']}\nНикнейм: @{mentor.get('username', 'Не указано')}\nСпециализация: {mentor.get('specialization', 'Не указано')}\nОпыт: {mentor.get('experience', 'Не указано')}"
    keyboard = [
        [InlineKeyboardButton("Написать ментору", callback_data=f"message_mentor_{mentor['telegram_id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=details, reply_markup=reply_markup)

async def send_message_to_mentor(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    target_id = int(query.data.split('_')[2])
    context.user_data['target_id'] = target_id  # Сохраняем ID ментора для отправки сообщения
    context.user_data['target_role'] = 'mentor'  # Указываем роль для уточнения логики отправки
    await query.edit_message_text(text="Введите сообщение для ментора:")

def setup_admin_handlers(application):
    application.add_handler(CommandHandler('admin', admin_panel))

    # Для пользователей
    application.add_handler(CallbackQueryHandler(view_users, pattern='^view_users$'))
    application.add_handler(CallbackQueryHandler(user_details, pattern='^user_'))
    application.add_handler(CallbackQueryHandler(send_message_to_user, pattern='^message_user_'))

    # Для менторов
    application.add_handler(CallbackQueryHandler(view_mentors, pattern='^view_mentors$'))
    application.add_handler(CallbackQueryHandler(mentor_details, pattern='^mentor_'))
    application.add_handler(CallbackQueryHandler(send_message_to_mentor, pattern='^message_mentor_'))