import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "aiogram"])
import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

from BotData.database_function import (
    add_user, get_users_by_gender, user_exists, add_like, is_mutual_like,
    get_user_by_id, get_new_support_requests, get_all_support_requests,
    clear_support_requests, mark_support_request_processed, create_tables,
    get_all_users, assign_admin_to_request, get_support_requests_for_admin,
    add_support_request, mark_support_request_deferred, delete_support_request,
    get_support_request_by_id # Эти функции удалены: save_broadcast_content, get_last_broadcast_content, clear_broadcast_content
)

from App.admin_keyboards import (
    admin, support_admin_menu, filter_menu, broadcast_confirm_keyboard, # Добавлена broadcast_confirm_keyboard
    request_actions_keyboard, confirm_clear_requests_keyboard, support_reason_keyboard
)

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN:", TOKEN)

# Инициализация бота
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Список админов и их специализации
# Список админов и их специализации
ADMINS_ROLES = {
    898352337: ["general_question", "technical_problem"], # Руслан: Общие вопросы, Технические проблемы
    1277578451: ["suggestions_ideas"],                     # Гульнур: Предложения/Идеи
    646559369: ["user_block", "profile_error"],             # Дамир: Блокировка пользователя, Ошибка в профиле
    # Добавьте других админов и их специализации.
    # Если админ не должен получать уведомления ни по какой причине, оставьте список пустым:
    # 123456789: [],
}
ADMINS = list(ADMINS_ROLES.keys()) # Список всех ID админов
ADMINS = list(ADMINS_ROLES.keys()) # Список всех ID админов

# Состояния для FSM
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_university = State()
    waiting_for_description = State()
    waiting_for_photo = State()

class SupportStates(StatesGroup):
    waiting_for_reason = State()
    waiting_for_support_description = State()
    waiting_for_admin_answer = State()
    waiting_for_broadcast_content = State()
    waiting_for_broadcast_confirmation = State() # Добавлено новое состояние

class SearchStates(StatesGroup):
    searching = State()

# --- КЛАВИАТУРЫ (НЕ ИЗМЕНЕНЫ ЗДЕСЬ, ОПРЕДЕЛЕНЫ В admin_keyboards.py) ---
gender_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Мужской'), KeyboardButton(text='Женский')]
], resize_keyboard=True)

main_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='❤️ Искать сожителя')],
    [KeyboardButton(text='✍️ Моя анкета')],
    [KeyboardButton(text='⚙️ Настройки')],
    [KeyboardButton(text='❓ Поддержка')]
], resize_keyboard=True)

profile_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Посмотреть анкету'), KeyboardButton(text='Редактировать анкету')],
    [KeyboardButton(text='Главное меню')]
], resize_keyboard=True)

back_to_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Главное меню')]
], resize_keyboard=True)

search_actions_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❤️ Лайк", callback_data="like")],
    [InlineKeyboardButton(text="➡️ Далее", callback_data="next_profile")],
    [InlineKeyboardButton(text="❌ Отмена поиска", callback_data="cancel_search")]
])

# --- ОБЩИЕ ФУНКЦИИ ---

async def send_profile(chat_id, user_data, keyboard, message_id=None):
    """Отправляет анкету пользователя."""
    if not user_data:
        await bot.send_message(chat_id, "Анкета не найдена.")
        return

    profile_text = (
        f"<b>Имя:</b> {user_data[2]}\n"
        f"<b>Возраст:</b> {user_data[3]}\n"
        f"<b>Пол:</b> {user_data[4]}\n"
        f"<b>Университет:</b> {user_data[5] or 'Не указан'}\n"
        f"<b>О себе:</b> {user_data[6] or 'Не указано'}"
    )

    if user_data[7]: # photo
        try:
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except TelegramBadRequest:
                    pass

            await bot.send_photo(chat_id, user_data[7], caption=profile_text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отправке фото анкеты: {e}")
            await bot.send_message(chat_id, profile_text + "\n(Фото не загружено или недоступно)", reply_markup=keyboard)
    else:
        try:
            if message_id and isinstance(keyboard, InlineKeyboardMarkup):
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=profile_text, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id, profile_text, reply_markup=keyboard)
                if message_id and not isinstance(keyboard, InlineKeyboardMarkup):
                    try:
                        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
                    except TelegramBadRequest:
                        pass
        except TelegramBadRequest as e:
            logging.warning(f"Не удалось отредактировать сообщение (ID: {message_id}): {e}. Отправляю новое.")
            await bot.send_message(chat_id, profile_text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отправке текстовой анкеты: {e}")
            await bot.send_message(chat_id, profile_text, reply_markup=keyboard)


# --- ОБРАБОТЧИКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---

@router.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    if not user_exists(message.from_user.id):
        await message.answer("Привет! Давай создадим твою анкету. Как тебя зовут?")
        await state.set_state(RegistrationStates.waiting_for_name)
    else:
        await message.answer("С возвращением! Что хочешь сделать?", reply_markup=main_menu_keyboard)
        await state.clear()

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegistrationStates.waiting_for_age)

@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        age = int(message.text)
        if 16 <= age <= 99:
            await state.update_data(age=age)
            await message.answer("Какой у тебя пол?", reply_markup=gender_keyboard)
            await state.set_state(RegistrationStates.waiting_for_gender)
        else:
            await message.answer("Пожалуйста, введите возраст от 16 до 99.")
    else:
        await message.answer("Пожалуйста, введите возраст числом.")

@router.message(RegistrationStates.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    if message.text in ['Мужской', 'Женский']:
        await state.update_data(gender=message.text)
        await message.answer("В каком университете ты учишься? (Напиши 'Пропустить', если не хочешь указывать)")
        await state.set_state(RegistrationStates.waiting_for_university)
    else:
        await message.answer("Пожалуйста, выберите пол, используя кнопки.")

@router.message(RegistrationStates.waiting_for_university)
async def process_university(message: types.Message, state: FSMContext):
    university = message.text if message.text.lower() != 'пропустить' else None
    await state.update_data(university=university)
    await message.answer("Расскажи немного о себе (увлечения, интересы, что ищешь в сожителе). Максимум 200 символов. (Напиши 'Пропустить', если не хочешь указывать)")
    await state.set_state(RegistrationStates.waiting_for_description)

@router.message(RegistrationStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text if message.text.lower() != 'пропустить' else None
    if description and len(description) > 200:
        await message.answer("Описание слишком длинное. Пожалуйста, сократите его до 200 символов.")
        return
    await state.update_data(description=description)
    await message.answer("Отправь своё фото.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegistrationStates.waiting_for_photo)

@router.message(RegistrationStates.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_data = await state.get_data()
    add_user(
        message.from_user.id,
        user_data['name'],
        user_data['age'],
        user_data['gender'],
        user_data['university'],
        user_data['description'],
        photo_id
    )
    await message.answer("Анкета создана! Что хочешь сделать?", reply_markup=main_menu_keyboard)
    await state.clear()

@router.message(RegistrationStates.waiting_for_photo, ~F.photo)
async def process_photo_invalid(message: types.Message):
    await message.answer("Пожалуйста, отправьте фотографию.")

@router.message(F.text == 'Главное меню')
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)

@router.message(F.text == '✍️ Моя анкета')
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user_by_id(user_id)
    if user_data:
        await send_profile(user_id, user_data, profile_keyboard)
    else:
        await message.answer("Ваша анкета не найдена. Возможно, вы ещё не зарегистрированы. Нажмите /start для регистрации.")

@router.message(F.text == '❤️ Искать сожителя')
async def start_search(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_user = get_user_by_id(user_id)
    if not current_user:
        await message.answer("Для поиска сначала создайте свою анкету, нажав /start.")
        return

    target_gender = "Женский" if current_user[4] == "Мужской" else "Мужской"
    profiles = get_users_by_gender(user_id, target_gender)

    if not profiles:
        await message.answer("К сожалению, пока нет анкет, подходящих под ваш запрос.", reply_markup=main_menu_keyboard)
        await state.clear()
        return

    await state.update_data(profiles=profiles, current_profile_index=0)
    await state.set_state(SearchStates.searching)

    first_profile = profiles[0]
    await send_profile(user_id, first_profile, search_actions_keyboard)

@router.callback_query(SearchStates.searching, F.data == 'like')
async def process_like(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    profiles = data['profiles']
    current_index = data['current_profile_index']
    
    if current_index >= len(profiles):
        await callback.message.answer("Профилей для лайка больше нет.", reply_markup=main_menu_keyboard)
        await state.clear()
        await callback.answer()
        return

    target_user_id = profiles[current_index][1]
    add_like(user_id, target_user_id)

    if is_mutual_like(user_id, target_user_id):
        target_user_info = get_user_by_id(target_user_id)
        requester_user_info = get_user_by_id(user_id)
        
        target_username_info = target_user_info[2] if target_user_info and target_user_info[2] else f"ID: {target_user_id}"
        requester_username_info = requester_user_info[2] if requester_user_info and requester_user_info[2] else f"ID: {user_id}"

        await callback.message.answer(f"🎉 Взаимный лайк! Вы можете связаться с этим человеком: {target_username_info}", reply_markup=search_actions_keyboard)
        
        if target_user_info:
            await bot.send_message(target_user_id, f"🎉 Взаимный лайк! Пользователь {requester_username_info} также поставил вам лайк!", reply_markup=main_menu_keyboard)
    else:
        await callback.message.answer("❤️ Лайк поставлен!", reply_markup=search_actions_keyboard)

    await process_next_profile(callback, state)
    await callback.answer()


@router.callback_query(SearchStates.searching, F.data == 'next_profile')
async def process_next_profile(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profiles = data['profiles']
    current_index = data['current_profile_index'] + 1

    if current_index < len(profiles):
        await state.update_data(current_profile_index=current_index)
        next_profile = profiles[current_index]
        await send_profile(callback.from_user.id, next_profile, search_actions_keyboard, callback.message.message_id)
    else:
        await callback.message.answer("Профилей больше нет. Возвращаемся в главное меню.", reply_markup=main_menu_keyboard)
        await state.clear()
    await callback.answer()

@router.callback_query(SearchStates.searching, F.data == 'cancel_search')
async def cancel_search(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Поиск отменён. Возвращаемся в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer()

@router.message(F.text == '❓ Поддержка')
async def choose_support_reason(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, выберите причину вашего обращения:", reply_markup=support_reason_keyboard)
    await state.set_state(SupportStates.waiting_for_reason)

@router.callback_query(SupportStates.waiting_for_reason, F.data.startswith('reason_'))
async def process_chosen_reason(callback: types.CallbackQuery, state: FSMContext):
    chosen_reason = callback.data.replace('reason_', '')

    if chosen_reason == 'cancel':
        await state.clear()
        await callback.message.edit_text("Обращение в поддержку отменено.", reply_markup=main_menu_keyboard)
        await callback.answer()
        return

    await state.update_data(reason=chosen_reason)
    await callback.message.edit_text("Отлично! Теперь опишите вашу проблему или вопрос. Пожалуйста, будьте максимально подробны.", reply_markup=None)
    await state.set_state(SupportStates.waiting_for_support_description)
    await callback.answer()

@router.message(SupportStates.waiting_for_support_description)
async def process_support_description(message: types.Message, state: FSMContext):
    request_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else str(user_id)

    data = await state.get_data()
    reason = data.get('reason')

    assigned_admin_id = None
    for admin_id, reasons_list in ADMINS_ROLES.items():
        if reason in reasons_list:
            assigned_admin_id = admin_id
            break
    
    if assigned_admin_id is None:
        assigned_admin_id = ADMINS[0] # По умолчанию назначаем главному админу, если нет специализированного

    request_id = add_support_request(user_id, username, request_text, reason, assigned_admin_id)

    if request_id:
        await message.answer("Ваше обращение отправлено. Мы рассмотрим его в ближайшее время.", reply_markup=main_menu_keyboard)
        await state.clear()

        try:
            reason_display_text = {
                "technical_problem": "⚙️ Техническая проблема",
                "profile_error": "📝 Ошибка в профиле",
                "user_block": "🔒 Блокировка пользователя",
                "suggestions_ideas": "💡 Предложения/Идея",
                "general_question": "❓ Общий вопрос"
            }.get(reason, reason)

            # Определяем, нужно ли отправлять прямое уведомление назначенному админу.
            # Уведомления отправляются только тем админам, чья роль включает эту причину.
            # Это позволяет главному админу (ADMINS[0]) не получать уведомления,
            # если он назначен как fallback и причина не в его ADMINS_ROLES.
            should_notify_assigned_admin = False
            if assigned_admin_id in ADMINS_ROLES and reason in ADMINS_ROLES[assigned_admin_id]:
                should_notify_assigned_admin = True
            elif assigned_admin_id == ADMINS[0] and not ADMINS_ROLES[ADMINS[0]]: # Если главный админ - fallback и у него нет причин в ролях
                logging.info(f"Запрос {request_id} (причина: {reason}) назначен главному админу ({assigned_admin_id}), но прямое уведомление не отправляется.")
                pass # Главный админ не получает прямое уведомление.

            if should_notify_assigned_admin:
                admin_username_text = ""
                try:
                    admin_info = await bot.get_chat(assigned_admin_id)
                    admin_username_text = f" (@{admin_info.username})" if admin_info.username else ""
                except Exception:
                    pass # Игнорируем ошибку получения имени пользователя, если его нет или приватный аккаунт.

                await bot.send_message(assigned_admin_id,
                                        f"❗️ Новое обращение в поддержку (ID: {request_id}):\n"
                                        f"От: @{username} (ID: <code>{user_id}</code>)\n"
                                        f"<b>Причина: {reason_display_text}</b>\n"
                                        f"Текст: {request_text}\n\n"
                                        f"Это обращение назначено вам.",
                                        reply_markup=request_actions_keyboard(request_id))

            # Убрано общее уведомление для главного админа, чтобы он видел все только по нажатию.
            # if assigned_admin_id != ADMINS[0]:
            #    try:
            #        await bot.send_message(ADMINS[0], ...)
            #    except Exception as e:
            #        logging.error(...)

        except Exception as e:
            logging.error(f"Не удалось отправить уведомление назначенному админу {assigned_admin_id}: {e}")
    else:
        await message.answer("Произошла ошибка при отправке вашего обращения. Пожалуйста, попробуйте позже.", reply_markup=main_menu_keyboard)
        await state.clear()

# --- ОБРАБОТЧИКИ ДЛЯ АДМИНОВ ---

@router.message(F.text == "/admin", F.from_user.id.in_(ADMINS))
async def admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin)

@router.message(F.text == '🔙 В админ-панель', F.from_user.id.in_(ADMINS))
async def back_to_admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в админ-панель.", reply_markup=admin)

@router.message(F.text == '📢 Создать рассылку', F.from_user.id.in_(ADMINS))
async def start_broadcast(message: types.Message, state: FSMContext):
    # Удаляем reply_markup=send
    await message.answer("Отправьте контент для рассылки (текст, фото, видео, документ с подписью).")
    await state.set_state(SupportStates.waiting_for_broadcast_content)
    # clear_broadcast_content() больше не нужен, так как храним в FSM

@router.message(SupportStates.waiting_for_broadcast_content, F.from_user.id.in_(ADMINS))
async def process_broadcast_content(message: types.Message, state: FSMContext):
    content = {}
    preview_text = "Вы хотите отправить эту рассылку?\n\n"

    if message.text:
        content["type"] = "text"
        content["text"] = message.text.strip()
        preview_text += f"Содержимое:\n`{content['text'][:200]}{'...' if len(content['text']) > 200 else ''}`"
    elif message.photo:
        content["type"] = "photo"
        content["file_id"] = message.photo[-1].file_id
        content["caption"] = message.caption or ""
        preview_text += f"Тип: Фото\nПодпись: `{content['caption'][:100]}{'...' if len(content['caption']) > 100 else ''}`"
    elif message.video:
        content["type"] = "video"
        content["file_id"] = message.video.file_id
        content["caption"] = message.caption or ""
        preview_text += f"Тип: Видео\nПодпись: `{content['caption'][:100]}{'...' if len(content['caption']) > 100 else ''}`"
    elif message.document:
        content["type"] = "document"
        content["file_id"] = message.document.file_id
        content["caption"] = message.caption or ""
        preview_text += f"Тип: Документ\nПодпись: `{content['caption'][:100]}{'...' if len(content['caption']) > 100 else ''}`"
    else:
        await message.answer("⚠️ Неподдерживаемый тип контента. Пожалуйста, отправьте текст, фото, видео или документ.", reply_markup=admin)
        await state.clear()
        return

    await state.update_data(broadcast_content=content)

    # Отправляем предпросмотр и кнопки подтверждения
    if content["type"] == "photo":
        await bot.send_photo(message.chat.id, content["file_id"], caption=preview_text, reply_markup=broadcast_confirm_keyboard)
    elif content["type"] == "video":
        await bot.send_video(message.chat.id, content["file_id"], caption=preview_text, reply_markup=broadcast_confirm_keyboard)
    elif content["type"] == "document":
        await bot.send_document(message.chat.id, content["file_id"], caption=preview_text, reply_markup=broadcast_confirm_keyboard)
    else: # text
        await message.answer(preview_text, reply_markup=broadcast_confirm_keyboard)

    # Переходим в состояние ожидания подтверждения рассылки
    await state.set_state(SupportStates.waiting_for_broadcast_confirmation)

@router.callback_query(F.data == 'broadcast_confirm_send', SupportStates.waiting_for_broadcast_confirmation, F.from_user.id.in_(ADMINS))
async def confirm_broadcast_send(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Начинаю рассылку...")

    broadcast_data = await state.get_data()
    content_to_send = broadcast_data.get('broadcast_content')

    if not content_to_send:
        await callback.message.edit_text("Ошибка: Нет контента для рассылки. Пожалуйста, попробуйте снова.", reply_markup=admin)
        await state.clear()
        return

    users = get_all_users()
    sent_count = 0
    failed_count = 0

    # Убираем кнопки и меняем текст/подпись сообщения-превью
    try:
        if content_to_send["type"] in ["photo", "video", "document"]:
            await callback.message.edit_caption(caption="Начинаю рассылку...", reply_markup=None)
        else: # text message
            await callback.message.edit_text("Начинаю рассылку...", reply_markup=None)
    except TelegramBadRequest:
        # Если сообщение уже изменено или удалено, просто отправляем новое.
        await callback.message.answer("Начинаю рассылку...", reply_markup=None)
    except Exception as e:
        logging.error(f"Ошибка при попытке изменить сообщение подтверждения: {e}")
        await callback.message.answer("Начинаю рассылку...", reply_markup=None)


    for user_id in users:
        try:
            if content_to_send["type"] == "text":
                await bot.send_message(user_id, content_to_send["text"])
            elif content_to_send["type"] == "photo":
                await bot.send_photo(user_id, content_to_send["file_id"], caption=content_to_send["caption"])
            elif content_to_send["type"] == "video":
                await bot.send_video(user_id, content_to_send["file_id"], caption=content_to_send["caption"])
            elif content_to_send["type"] == "document":
                await bot.send_document(user_id, content_to_send["file_id"], caption=content_to_send["caption"])
            sent_count += 1
            await asyncio.sleep(0.05) # Небольшая задержка, чтобы не превысить лимиты Telegram
        except Exception as e:
            logging.error(f"Не удалось отправить рассылку пользователю {user_id}: {e}")
            failed_count += 1
        finally:
            await asyncio.sleep(0.05) # Дополнительная задержка

    await callback.message.answer(f"Рассылка завершена!\nОтправлено: {sent_count}\nНе удалось: {failed_count}", reply_markup=admin)
    await state.clear()
    # clear_broadcast_content() больше не нужен

@router.callback_query(F.data == 'broadcast_cancel', SupportStates.waiting_for_broadcast_confirmation, F.from_user.id.in_(ADMINS))
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        # Пытаемся отредактировать сообщение с кнопками, чтобы убрать их
        if callback.message.caption: # Если это было медиа с подписью
            await callback.message.edit_caption(caption="Рассылка отменена.", reply_markup=None)
        else: # Если это был просто текст
            await callback.message.edit_text("Рассылка отменена.", reply_markup=None)
    except TelegramBadRequest:
        # Если не удалось отредактировать (например, сообщение слишком старое), отправляем новое
        await callback.message.answer("Рассылка отменена.", reply_markup=admin)
    except Exception as e:
        logging.error(f"Ошибка при отмене рассылки: {e}")
        await callback.message.answer("Рассылка отменена.", reply_markup=admin)

    await callback.answer()
    # clear_broadcast_content() больше не нужен

@router.message(F.text == '📋 Управление обращениями', F.from_user.id.in_(ADMINS))
async def manage_requests(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите действие с обращениями:", reply_markup=support_admin_menu)

@router.message(F.text == '📥 Просмотреть обращения', F.from_user.id.in_(ADMINS))
async def view_requests(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    if admin_id == ADMINS[0]: # Если это главный админ
        await message.answer("Выберите фильтр для просмотра обращений:", reply_markup=filter_menu)
    else: # Для других админов показываем только их обращения
        assigned_reasons = ADMINS_ROLES.get(admin_id, [])
        requests = get_support_requests_for_admin(admin_id=admin_id, reasons=assigned_reasons)
        if requests:
            await state.update_data(requests=requests, current_request_index=0)
            await display_request(message.chat.id, requests[0], message.message_id)
        else:
            await message.answer("Нет новых или отложенных обращений, назначенных вам.", reply_markup=support_admin_menu)


@router.callback_query(F.data.startswith('filter_'), F.from_user.id == ADMINS[0])
async def handle_filter(callback: types.CallbackQuery, state: FSMContext):
    admin_id = callback.from_user.id
    filter_type = callback.data.split('_')[1]
    requests = []
    
    if filter_type == 'all_active':
        # Главный админ может видеть все активные и отложенные обращения
        requests = get_support_requests_for_admin(admin_id=None, include_processed=False)
    elif filter_type == 'tech':
        requests = get_support_requests_for_admin(admin_id=None, reasons=['technical_problem'], include_processed=False)
    elif filter_type == 'profile':
        requests = get_support_requests_for_admin(admin_id=None, reasons=['profile_error'], include_processed=False)
    elif filter_type == 'block':
        requests = get_support_requests_for_admin(admin_id=None, reasons=['user_block'], include_processed=False)
    elif filter_type == 'idea':
        requests = get_support_requests_for_admin(admin_id=None, reasons=['suggestions_ideas'], include_processed=False)
    elif filter_type == 'back':
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Выберите действие с обращениями:", reply_markup=support_admin_menu)
        await state.clear()
        await callback.answer()
        return

    if requests:
        await state.update_data(requests=requests, current_request_index=0)
        await display_request(callback.message.chat.id, requests[0], callback.message.message_id)
    else:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("По выбранному фильтру нет активных обращений.", reply_markup=support_admin_menu)
    await callback.answer()

async def display_request(chat_id, req_data, message_id=None):
    request_id = req_data[0]
    user_id = req_data[1]
    username = req_data[2]
    request_text = req_data[3]
    timestamp = req_data[4]
    is_processed = req_data[5]
    reason = req_data[6]
    assigned_admin = req_data[7]

    status = {0: "Не обработано", 1: "Обработано", 2: "Отложено"}.get(is_processed, "Неизвестно")

    reason_display = {
        "technical_problem": "⚙️ Техническая проблема",
        "profile_error": "📝 Ошибка в профиле",
        "user_block": "🔒 Блокировка пользователя",
        "suggestions_ideas": "💡 Предложения/Идея",
        "general_question": "❓ Общий вопрос"
    }.get(reason, reason)

    admin_username = ""
    if assigned_admin:
        try:
            admin_info = await bot.get_chat(assigned_admin)
            admin_username = f" (@{admin_info.username})" if admin_info.username else ""
        except Exception:
            admin_username = ""

    text = (
        f"<b>Обращение #{request_id}</b>\n"
        f"От: @{username} (ID: <code>{user_id}</code>)\n"
        f"Время: {timestamp}\n"
        f"Статус: {status}\n"
        f"Причина: {reason_display}\n"
        f"Назначен админ: {assigned_admin}{admin_username if admin_username else ''}\n\n"
        f"<b>Текст обращения:</b>\n{request_text}"
    )

    try:
        if message_id:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=request_actions_keyboard(request_id))
        else:
            await bot.send_message(chat_id, text, reply_markup=request_actions_keyboard(request_id))
    except TelegramBadRequest as e:
        logging.warning(f"Не удалось отредактировать сообщение (ID: {message_id}) при отображении запроса: {e}. Отправляю новое.")
        await bot.send_message(chat_id, text, reply_markup=request_actions_keyboard(request_id))
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения с обращением: {e}")
        await bot.send_message(chat_id, text, reply_markup=request_actions_keyboard(request_id))


@router.callback_query(F.data.startswith(('answer_request:', 'process_request:', 'defer_request:', 'delete_request:')), F.from_user.id.in_(ADMINS))
async def process_request_actions(callback: types.CallbackQuery, state: FSMContext):
    action, request_id_str = callback.data.split(':')
    request_id = int(request_id_str)
    admin_id = callback.from_user.id

    req_info = get_support_request_by_id(request_id)
    if not req_info:
        await callback.message.edit_text(f"Обращение #{request_id} не найдено или уже было удалено.", reply_markup=support_admin_menu)
        await callback.answer()
        return

    if action == 'answer_request':
        await callback.message.edit_text("Введите ваш ответ пользователю. Этот ответ будет отправлен пользователю, а обращение будет помечено как обработанное. Для отмены напишите 'Отмена'.", reply_markup=None)
        await state.set_state(SupportStates.waiting_for_admin_answer)
        await state.update_data(current_request_id=request_id, original_message_id=callback.message.message_id, original_chat_id=callback.message.chat.id)
    
    elif action == 'process_request':
        if mark_support_request_processed(request_id):
            user_id_of_requester = req_info[1]
            try:
                await bot.send_message(user_id_of_requester, f"✅ Ваше обращение #{request_id} было обработано. Спасибо за ожидание!")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {user_id_of_requester}: {e}")
            
            try:
                await callback.message.edit_text(f"Обращение #{request_id} помечено как обработанное и уведомление отправлено пользователю.\n\nБыло: {req_info[3]}", reply_markup=None)
            except TelegramBadRequest as e:
                logging.warning(f"Не удалось отредактировать сообщение после обработки запроса: {e}. Отправляю новое.")
                await callback.message.answer(f"Обращение #{request_id} помечено как обработанное и уведомление отправлено пользователю.\n\nБыло: {req_info[3]}", reply_markup=support_admin_menu)
            
            await state.clear()
        else:
            await callback.message.edit_text(f"Ошибка при обработке обращения #{request_id}.", reply_markup=support_admin_menu)
        
    elif action == 'defer_request':
        if mark_support_request_deferred(request_id):
            try:
                await callback.message.edit_text(f"Обращение #{request_id} отложено.\n\nБыло: {req_info[3]}", reply_markup=None)
            except TelegramBadRequest as e:
                logging.warning(f"Не удалось отредактировать сообщение после откладывания запроса: {e}. Отправляю новое.")
                await callback.message.answer(f"Обращение #{request_id} отложено.\n\nБыло: {req_info[3]}", reply_markup=support_admin_menu)
            
            await state.clear()
        else:
            await callback.message.edit_text(f"Ошибка при откладывании обращения #{request_id}.", reply_markup=support_admin_menu)
        
    elif action == 'delete_request':
        if delete_support_request(request_id):
            try:
                await callback.message.delete()
                await callback.message.answer(f"Обращение #{request_id} удалено.", reply_markup=support_admin_menu)
            except Exception as e:
                logging.error(f"Не удалось удалить сообщение для админа после удаления запроса: {e}")
                await callback.message.edit_text(f"Обращение #{request_id} удалено (не удалось удалить сообщение из чата).", reply_markup=support_admin_menu)
        else:
            await callback.message.edit_text(f"Ошибка при удалении обращения #{request_id}.", reply_markup=support_admin_menu)
        await state.clear()
    
    await callback.answer()


@router.message(SupportStates.waiting_for_admin_answer, F.from_user.id.in_(ADMINS))
async def process_admin_answer(message: types.Message, state: FSMContext):
    admin_answer = message.text
    data = await state.get_data()
    request_id = data.get('current_request_id')
    original_message_id = data.get('original_message_id')
    original_chat_id = data.get('original_chat_id')

    if not request_id:
        await message.answer("Произошла ошибка: не найден ID обращения. Пожалуйста, попробуйте снова.", reply_markup=support_admin_menu)
        await state.clear()
        return
    
    if admin_answer.lower() == "отмена":
        await message.answer("Ответ отменен.", reply_markup=support_admin_menu)
        if original_message_id and original_chat_id:
            req_info_after_cancel = get_support_request_by_id(request_id)
            if req_info_after_cancel:
                try:
                    await display_request(original_chat_id, req_info_after_cancel, original_message_id)
                except Exception as e:
                    logging.warning(f"Не удалось восстановить сообщение с кнопками после отмены ответа: {e}")
        await state.clear()
        return

    target_request = get_support_request_by_id(request_id)

    if target_request:
        user_id_of_requester = target_request[1]
        try:
            await bot.send_message(user_id_of_requester, f"✉️ Ответ по вашему обращению #{request_id}:\n\n{admin_answer}")
            mark_support_request_processed(request_id)
            await message.answer(f"Ответ пользователю по обращению #{request_id} отправлен и обращение помечено как обработанное.", reply_markup=support_admin_menu)
            
            if original_message_id and original_chat_id:
                try:
                    await bot.edit_message_text(
                        chat_id=original_chat_id,
                        message_id=original_message_id,
                        text=f"Обращение #{request_id} обработано админом и ответ отправлен.\n\nИсходный текст: {target_request[3]}",
                        reply_markup=None
                    )
                except TelegramBadRequest as e:
                    logging.warning(f"Не удалось отредактировать сообщение (ID: {original_message_id}) после отправки ответа: {e}.")
        except Exception as e:
            logging.error(f"Не удалось отправить ответ пользователю {user_id_of_requester}: {e}")
            await message.answer("Не удалось отправить ответ пользователю. Возможно, бот заблокирован или пользователь недоступен.", reply_markup=support_admin_menu)
    else:
        await message.answer("Не удалось найти обращение для отправки ответа.", reply_markup=support_admin_menu)

    await state.clear()


@router.message(F.text == '🗑️ Очистить обращения', F.from_user.id.in_(ADMINS))
async def confirm_clear_all_requests(message: types.Message):
    await message.answer("Вы уверены, что хотите удалить ВСЕ обращения? Это действие необратимо.", reply_markup=confirm_clear_requests_keyboard)

@router.callback_query(F.data == 'confirm_clear_requests', F.from_user.id.in_(ADMINS))
async def clear_all_requests_confirmed(callback: types.CallbackQuery, state: FSMContext):
    if clear_support_requests():
        await callback.message.edit_text("Все обращения удалены.", reply_markup=support_admin_menu)
    else:
        await callback.message.edit_text("Ошибка при удалении обращений.", reply_markup=support_admin_menu)
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == 'cancel_clear_requests', F.from_user.id.in_(ADMINS))
async def clear_all_requests_cancelled(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Очистка обращений отменена.", reply_markup=support_admin_menu)
    await callback.answer()
    await state.clear()


# Запуск бота
async def main():
    create_tables()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())