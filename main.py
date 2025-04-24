import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from environs import Env
from BotData.database_function import add_user, get_users_by_gender, user_exists, add_like, is_mutual_like, get_user_by_id, create_tables, count_likes, get_likers, delete_user, delete_all_profiles, update_photo_in_db, update_description_in_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загрузка конфигурации из .env
print("Чтение .env...")
env = Env()
env.read_env()
BOT_TOKEN = env('BOT_TOKEN')
print(f"Токен: {BOT_TOKEN[:10]}...")

# Инициализация бота
print("Инициализация бота...")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ID администратора
ADMIN_ID = 898352337  # Ваш telegram_id

# Словарь для хранения данных о поиске и просмотре лайков
user_data = {}

# FSM для регистрации
class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    university = State()
    description = State()
    photo = State()

# FSM для редактирования фото
class EditPhotoState(StatesGroup):
    waiting_for_photo = State()

# FSM для редактирования описания
class EditDescriptionState(StatesGroup):
    waiting_for_description = State()

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Поиск сожителя")],
        [KeyboardButton(text="🔧 Редактировать профиль"), KeyboardButton(text="👤 Мой профиль")]
    ],
    resize_keyboard=True
)

# Меню редактирования профиля
edit_profile_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Изменить фото")],
        [KeyboardButton(text="✏️ Изменить описание")],
        [KeyboardButton(text="📝 Заполнить анкету заново")],
        [KeyboardButton(text="🔙 В главное меню")]
    ],
    resize_keyboard=True
)

# Клавиатура выбора пола
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")]
    ],
    resize_keyboard=True
)

# Клавиатура для поиска и просмотра лайков
match_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Лайк"), KeyboardButton(text="❌ Дизлайк")],
        [KeyboardButton(text="⛔ Прекратить просмотр")]
    ],
    resize_keyboard=True
)

# Обработчик команды /start
@dp.message(F.text == "/start")
async def start_command(message: types.Message, state: FSMContext):
    print(f"Получена команда /start от {message.from_user.id}")
    logging.info(f"Получена команда /start от {message.from_user.id}")
    if user_exists(message.from_user.id):
        await message.answer("Выбери действие:", reply_markup=main_menu)
    else:
        await message.answer("Привет! Давай начнём регистрацию. Как тебя зовут?")
        await state.set_state(Registration.name)

# Команда для очистки базы данных (только для админа)
@dp.message(F.text == "/clear_db")
async def clear_database(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return
    try:
        if delete_all_profiles():
            await message.answer("База данных успешно очищена.")
        else:
            await message.answer("Ошибка при очистке базы данных. Проверьте логи.")
    except Exception as e:
        logging.error(f"Ошибка при очистке базы данных: {e}")
        await message.answer("Произошла ошибка при очистке базы данных.")

# Показ профиля пользователя
@dp.message(F.text == "👤 Мой профиль")
async def show_my_profile(message: types.Message):
    user = get_user_by_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Зарегистрируйтесь через /start.")
        return
    try:
        caption = (
            f"👤 {user[2]}, {user[3]} лет\n"
            f"🏫 {user[5]}\n"
            f"📌 {user[6]}"
        )
        await message.answer_photo(user[7], caption=caption, reply_markup=main_menu)
    except Exception as e:
        logging.error(f"Ошибка при отправке профиля {message.from_user.id}: {e}")
        await message.answer("Не удалось загрузить ваш профиль. Попробуйте позже.", reply_markup=main_menu)

# Регистрация: обработка имени
@dp.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.age)

# Регистрация: обработка возраста
@dp.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число.")
        return
    age = int(message.text)
    if not (12 <= age <= 100):
        await message.answer("Введите реальный возраст (12-100 лет).")
        return
    await state.update_data(age=age)
    await message.answer("Выбери свой пол:", reply_markup=gender_keyboard)
    await state.set_state(Registration.gender)

# Регистрация: обработка пола
@dp.message(Registration.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if message.text not in ["Мужской", "Женский"]:
        await message.answer("Пожалуйста, выбери пол кнопкой ниже.")
        return
    await state.update_data(gender=message.text)
    await message.answer("Где ты учишься?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.university)

# Регистрация: обработка университета
@dp.message(Registration.university)
async def process_university(message: types.Message, state: FSMContext):
    await state.update_data(university=message.text)
    await message.answer("Добавь краткое описание о себе.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.description)

# Регистрация: обработка описания
@dp.message(Registration.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Пришли своё фото.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.photo)

# Регистрация: обработка фото
@dp.message(Registration.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте изображение.")
        return

    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    try:
        if add_user(
            telegram_id=message.from_user.id,
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            university=data['university'],
            description=data['description'],
            photo=photo_id
        ):
            await message.answer("Регистрация завершена! Теперь выбери действие:", reply_markup=main_menu)
        else:
            await message.answer("Ошибка: вы уже зарегистрированы.")
    except Exception as e:
        logging.error(f"Ошибка при регистрации {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при регистрации. Попробуйте снова.")
    finally:
        await state.clear()

# Редактирование профиля
@dp.message(F.text == "🔧 Редактировать профиль")
async def edit_profile(message: types.Message):
    await message.answer("Выбери, что хочешь изменить:", reply_markup=edit_profile_menu)

# Возврат в главное меню
@dp.message(F.text == "🔙 В главное меню")
async def return_to_main(message: types.Message):
    await message.answer("Возвращаемся в главное меню.", reply_markup=main_menu)

# Изменение фото
@dp.message(F.text == "📸 Изменить фото")
async def prompt_edit_photo(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, пришлите новое фото.")
    await state.set_state(EditPhotoState.waiting_for_photo)

@dp.message(EditPhotoState.waiting_for_photo, F.content_type == types.ContentType.PHOTO)
async def process_new_photo(message: types.Message, state: FSMContext):
    new_photo_id = message.photo[-1].file_id
    try:
        if update_photo_in_db(message.from_user.id, new_photo_id):
            await message.answer("Фото успешно обновлено!", reply_markup=main_menu)
        else:
            await message.answer("Не удалось обновить фото. Попробуйте снова.", reply_markup=main_menu)
    except Exception as e:
        logging.error(f"Ошибка при обновлении фото {message.from_user.id}: {e}")
        await message.answer("Не удалось обновить фото. Попробуйте снова.", reply_markup=main_menu)
    finally:
        await state.clear()

# Изменение описания
@dp.message(F.text == "✏️ Изменить описание")
async def prompt_edit_description(message: types.Message, state: FSMContext):
    await message.answer("Напишите новое описание.")
    await state.set_state(EditDescriptionState.waiting_for_description)

@dp.message(EditDescriptionState.waiting_for_description)
async def process_new_description(message: types.Message, state: FSMContext):
    new_description = message.text
    try:
        if update_description_in_db(message.from_user.id, new_description):
            await message.answer("Описание успешно обновлено!", reply_markup=main_menu)
        else:
            await message.answer("Не удалось обновить описание. Попробуйте снова.", reply_markup=main_menu)
    except Exception as e:
        logging.error(f"Ошибка при обновлении описания {message.from_user.id}: {e}")
        await message.answer("Не удалось обновить описание. Попробуйте снова.", reply_markup=main_menu)
    finally:
        await state.clear()

# Заполнение анкеты заново
@dp.message(F.text == "📝 Заполнить анкету заново")
async def re_register(message: types.Message, state: FSMContext):
    try:
        if delete_user(message.from_user.id):
            await message.answer("Анкета удалена. Давай начнём заново. Как тебя зовут?")
            await state.set_state(Registration.name)
        else:
            await message.answer("Не удалось удалить анкету. Попробуйте снова.", reply_markup=main_menu)
    except Exception as e:
        logging.error(f"Ошибка при удалении анкеты {message.from_user.id}: {e}")
        await message.answer("Не удалось удалить анкету. Попробуйте снова.", reply_markup=main_menu)

# Поиск сожителя
@dp.message(F.text == "🔎 Поиск сожителя")
async def start_search(message: types.Message):
    user_id = message.from_user.id
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT gender FROM users WHERE telegram_id = ?", (user_id,))
        res = cursor.fetchone()

        if not res:
            await message.answer("Ты не зарегистрирован. Используй /start.")
            return

        user_gender = res[0]
        candidates = get_users_by_gender(user_gender, user_id)
        conn.close()

        if not candidates:
            await message.answer("Нет доступных анкет. Попробуй позже.", reply_markup=main_menu)
            return

        # Сохраняем данные поиска
        user_data[user_id] = {"roommates": candidates, "index": 0, "mode": "search"}
        await message.answer("Начинаем поиск...", reply_markup=match_keyboard)
        await show_profile(message, user_id=user_id)
    except Exception as e:
        logging.error(f"Ошибка при начале поиска {user_id}: {e}")
        await message.answer("Произошла ошибка при поиске. Попробуйте снова.", reply_markup=main_menu)

# Просмотр лайкнувших (через инлайн-кнопку)
@dp.callback_query(F.data == "view_likers")
async def start_view_likers(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        if not user_exists(user_id):
            await callback.message.answer("Ты не зарегистрирован. Используй /start.", reply_markup=main_menu)
            await callback.answer()
            return

        likers = get_likers(user_id)
        logging.info(f"Получены лайкеры для {user_id}: {len(likers)}")

        if not likers:
            await callback.message.answer("Пока никто не лайкнул твою анкету.", reply_markup=main_menu)
            await callback.answer()
            return

        # Сохраняем данные для просмотра лайков
        user_data[user_id] = {"roommates": likers, "index": 0, "mode": "likers"}
        logging.info(f"Сохранены данные для просмотра лайков для {user_id}: {user_data[user_id]}")
        
        await callback.message.answer("Смотрим, кто тебя лайкнул...", reply_markup=match_keyboard)
        await show_profile(callback.message, user_id=user_id)
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка при просмотре лайкнувших {user_id}: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=main_menu)
        await callback.answer()

# Функция показа анкеты
async def show_profile(message: types.Message, user_id: int = None):
    user_id = user_id or message.from_user.id
    data = user_data.get(user_id)

    if not data:
        logging.error(f"Просмотр не запущен для {user_id}. user_data: {user_data}")
        await message.answer("Просмотр не запущен.", reply_markup=main_menu)
        return

    index = data["index"]
    if index >= len(data["roommates"]):
        logging.info(f"Анкеты закончились для {user_id}")
        await message.answer("Анкеты закончились!", reply_markup=main_menu)
        del user_data[user_id]
        return

    roommate = data["roommates"][index]
    user_data[user_id]["index"] += 1

    try:
        caption = f"👤 {roommate[2]}, {roommate[3]} лет\n🏫 {roommate[5]}\n📌 {roommate[6]}"
        if data["mode"] == "likers":
            caption += "\n✅ Этот пользователь лайкнул тебя!"
        await message.answer_photo(roommate[7], caption=caption, reply_markup=match_keyboard)
    except Exception as e:
        logging.error(f"Ошибка при показе анкеты {roommate[1]} для {user_id}: {e}")
        await message.answer("Не удалось загрузить анкету. Переходим к следующей.", reply_markup=match_keyboard)
        await show_profile(message, user_id=user_id)

# Обработка лайка
@dp.message(F.text == "❤️ Лайк")
async def like_profile(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id)
    if not data:
        await message.answer("Просмотр не запущен.", reply_markup=main_menu)
        return

    index = data["index"] - 1
    if index < 0 or index >= len(data["roommates"]):
        await message.answer("Анкеты закончились!", reply_markup=main_menu)
        del user_data[user_id]
        return

    roommate = data["roommates"][index]
    liked_user_id = roommate[1]

    try:
        add_like(user_id, liked_user_id)
        logging.info(f"Добавлен лайк от {user_id} к {liked_user_id}")

        # Отправляем уведомление пользователю о новом лайке
        try:
            total_likes = count_likes(liked_user_id)
            notification_text = f"❤️ Вам поставили лайк! Всего у вас {total_likes} лайк(ов)."
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Посмотреть, кто лайкнул", callback_data="view_likers")]
            ])
            await bot.send_message(chat_id=liked_user_id, text=notification_text, reply_markup=inline_keyboard)
            logging.info(f"Отправлено уведомление о лайке пользователю {liked_user_id}")
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление о лайке пользователю {liked_user_id}: {e}")

        # Проверяем взаимный лайк
        mutual_like = is_mutual_like(user_id, liked_user_id)
        logging.info(f"Взаимный лайк между {user_id} и {liked_user_id}: {mutual_like}")
        if mutual_like:
            # Отправляем анкету пользователю А (текущему пользователю)
            matched_user = get_user_by_id(liked_user_id)
            if not matched_user:
                logging.error(f"Пользователь {liked_user_id} не найден в базе данных")
                await message.answer("Ошибка: данные пользователя не найдены.", reply_markup=match_keyboard)
                await show_profile(message, user_id=user_id)
                return

            try:
                chat = await bot.get_chat(liked_user_id)
                username_info = f"@{chat.username}" if chat.username else "Юзернейм не указан"
                caption = (
                    f"🎉 У вас метч!\n"
                    f"👤 {matched_user[2]}, {matched_user[3]} лет\n"
                    f"🏫 {matched_user[5]}\n"
                    f"📌 {matched_user[6]}\n"
                    f"🔖 Юзернейм: {username_info}"
                )
                await message.answer_photo(matched_user[7], caption=caption)
                logging.info(f"Отправлена анкета {liked_user_id} пользователю {user_id} из-за взаимного лайка")
            except Exception as e:
                logging.error(f"Ошибка при отправке анкеты {liked_user_id} пользователю {user_id}: {e}")

            # Отправляем анкету пользователя А пользователю Б
            current_user = get_user_by_id(user_id)
            if not current_user:
                logging.error(f"Пользователь {user_id} не найден в базе данных")
                await message.answer("Ошибка: данные текущего пользователя не найдены.", reply_markup=match_keyboard)
                await show_profile(message, user_id=user_id)
                return

            try:
                chat_current = await bot.get_chat(user_id)
                username_info_current = f"@{chat_current.username}" if chat_current.username else "Юзернейм не указан"
                caption_current = (
                    f"🎉 У вас метч!\n"
                    f"👤 {current_user[2]}, {current_user[3]} лет\n"
                    f"🏫 {current_user[5]}\n"
                    f"📌 {current_user[6]}\n"
                    f"🔖 Юзернейм: {username_info_current}"
                )
                await bot.send_photo(
                    chat_id=liked_user_id,
                    photo=current_user[7],
                    caption=caption_current
                )
                logging.info(f"Отправлена анкета {user_id} пользователю {liked_user_id} из-за взаимного лайка")
            except Exception as e:
                logging.error(f"Ошибка при отправке анкеты {user_id} пользователю {liked_user_id}: {e}")

        await show_profile(message, user_id=user_id)
    except Exception as e:
        logging.error(f"Ошибка при обработке лайка {user_id} -> {liked_user_id}: {e}")
        await message.answer("Произошла ошибка при обработке лайка. Попробуйте снова.", reply_markup=match_keyboard)
        await show_profile(message, user_id=user_id)
        
# Обработка дизлайка
@dp.message(F.text == "❌ Дизлайк")
async def dislike_profile(message: types.Message):
    user_id = message.from_user.id
    try:
        await show_profile(message, user_id=user_id)
    except Exception as e:
        logging.error(f"Ошибка при обработке дизлайка {user_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.", reply_markup=main_menu)

# Остановить просмотр
@dp.message(F.text == "⛔ Прекратить просмотр")
async def stop_view(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
        await message.answer("Просмотр остановлен.", reply_markup=main_menu)
    else:
        await message.answer("Ты ещё не начинал просмотр.", reply_markup=main_menu)

# Запуск бота
async def main():
    try:
        print("Создание таблиц базы данных...")
        create_tables()
        logging.info("База данных настроена")
        print("Запуск polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    try:
        print("Запуск бота...")
        asyncio.run(main())
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка: {e}")
