from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton, InlineKeyboardMarkup)

# Основное меню админа
admin = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='📢 Создать рассылку')],
    [KeyboardButton(text='📋 Управление обращениями')]
], resize_keyboard=True)

# Меню управления обращениями
support_admin_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='📥 Просмотреть обращения')],
    [KeyboardButton(text='🗑️ Очистить обращения')],
    [KeyboardButton(text='🔙 В админ-панель')]
], resize_keyboard=True)

# Фильтры для просмотра обращений (для основного админа)
filter_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📋 Все обращения", callback_data="filter_all_active")],
    [InlineKeyboardButton(text="⚙️ Техническая проблема", callback_data="filter_technical_problem")],
    [InlineKeyboardButton(text="📝 Ошибка в профиле", callback_data="filter_profile_error")],
    [InlineKeyboardButton(text="🔒 Блокировка пользователя", callback_data="filter_user_block")],
    [InlineKeyboardButton(text="💡 Предложения/Идея", callback_data="filter_suggestions_ideas")],
    [InlineKeyboardButton(text="❓ Общий вопрос", callback_data="filter_general_question")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="filter_back")]
])

# Клавиатура для подтверждения рассылки (ИНЛАЙН)
broadcast_confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Отправить рассылку", callback_data="broadcast_confirm_send")],
    [InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")]
])

# Зарезервировано для будущих функций (например, блокировки пользователей)
report = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Заблокировать анкету'), KeyboardButton(text='Далее'), KeyboardButton(text='Выйти')]\
], resize_keyboard=True)

# Клавиатура для действий с запросом (нужно убедиться, что она корректно генерируется с request_id)
def request_actions_keyboard(request_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"answer_request:{request_id}")],
        [InlineKeyboardButton(text="Обработано", callback_data=f"process_request:{request_id}")],
        [InlineKeyboardButton(text="Отложить", callback_data=f"defer_request:{request_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_request:{request_id}")]
    ])

# Клавиатура для подтверждения очистки запросов
confirm_clear_requests_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да, удалить все", callback_data="confirm_clear_requests")],
    [InlineKeyboardButton(text="Нет, отмена", callback_data="cancel_clear_requests")]
])

# Клавиатура для выбора причины обращения в поддержку
support_reason_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚙️ Техническая проблема", callback_data="reason_technical_problem")],
    [InlineKeyboardButton(text="📝 Ошибка в профиле", callback_data="reason_profile_error")],
    [InlineKeyboardButton(text="🔒 Блокировка пользователя", callback_data="reason_user_block")],
    [InlineKeyboardButton(text="💡 Предложения/Идея", callback_data="reason_suggestions_ideas")],
    [InlineKeyboardButton(text="❓ Общий вопрос", callback_data="reason_general_question")],
    [InlineKeyboardButton(text="❌ Отмена", callback_data="reason_cancel")]
])