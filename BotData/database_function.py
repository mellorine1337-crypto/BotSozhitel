import sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Создаём БД и таблицы
def create_tables():
    """
    Создаёт необходимые таблицы в базе данных, если они ещё не существуют.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            # Таблица пользователей (добавлены housing_prefs и registered_at)
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                telegram_id INTEGER UNIQUE,
                                name TEXT,
                                age INTEGER,
                                gender TEXT,
                                university TEXT,
                                description TEXT,
                                photo TEXT,
                                housing_prefs TEXT,
                                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )''')

            # Таблица для хранения города (Алматы)
            cursor.execute('''CREATE TABLE IF NOT EXISTS location (
                                telegram_id INTEGER PRIMARY KEY,
                                city TEXT DEFAULT 'Алматы'
                            )''')

            # Таблица лайков
            cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
                                from_id INTEGER,
                                to_id INTEGER,
                                PRIMARY KEY (from_id, to_id)
                            )''')

            # Таблица обращений в поддержку
            cursor.execute('''CREATE TABLE IF NOT EXISTS support_requests (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                username TEXT,
                                request_text TEXT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                is_processed INTEGER DEFAULT 0,
                                reason TEXT,
                                assigned_admin INTEGER
                            )''')

            conn.commit()
            logging.info("Таблицы успешно созданы или уже существуют.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблиц: {e}")


# Функции для работы с пользователями (без изменений)
def add_user(telegram_id, name, age, gender, university, description, photo):
    """
    Добавляет нового пользователя в базу данных.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (telegram_id, name, age, gender, university, description, photo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (telegram_id, name, age, gender, university, description, photo))
            conn.commit()
            logging.info(f"Пользователь {name} ({telegram_id}) добавлен в БД.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Пользователь с Telegram ID {telegram_id} уже существует.")
            return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")
            return False

def user_exists(telegram_id):
    """
    Проверяет, существует ли пользователь с данным Telegram ID.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
        return cursor.fetchone() is not None

def get_user_by_id(telegram_id):
    """
    Возвращает информацию о пользователе по его Telegram ID.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return cursor.fetchone()

def get_users_by_gender(current_user_id, target_gender):
    """
    Возвращает список пользователей указанного пола, исключая текущего пользователя.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        # Исключаем пользователей, которым текущий пользователь уже ставил лайк
        # и самого текущего пользователя
        cursor.execute("""
            SELECT * FROM users
            WHERE gender = ? AND telegram_id != ?
            AND telegram_id NOT IN (SELECT to_id FROM likes WHERE from_id = ?)
        """, (target_gender, current_user_id, current_user_id))
        return cursor.fetchall()

def get_all_users():
    """
    Возвращает список всех зарегистрированных пользователей.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        return [row[0] for row in cursor.fetchall()]

# Функции для работы с лайками (без изменений)
def add_like(from_id, to_id):
    """
    Добавляет лайк от одного пользователя другому.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO likes (from_id, to_id) VALUES (?, ?)", (from_id, to_id))
            conn.commit()
            logging.info(f"Пользователь {from_id} поставил лайк {to_id}.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Лайк от {from_id} к {to_id} уже существует.")
            return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении лайка: {e}")
            return False

def is_mutual_like(user1_id, user2_id):
    """
    Проверяет наличие взаимного лайка между двумя пользователями.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM likes WHERE from_id = ? AND to_id = ?", (user1_id, user2_id))
        like1 = cursor.fetchone()
        cursor.execute("SELECT 1 FROM likes WHERE from_id = ? AND to_id = ?", (user2_id, user1_id))
        like2 = cursor.fetchone()
        return like1 is not None and like2 is not None

# Функции для работы с обращениями в поддержку
def add_support_request(user_id, username, request_text, reason=None, assigned_admin=None):
    """
    Добавляет новое обращение в поддержку.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO support_requests (user_id, username, request_text, reason, assigned_admin) VALUES (?, ?, ?, ?, ?)",
                           (user_id, username, request_text, reason, assigned_admin))
            conn.commit()
            logging.info(f"Добавлено новое обращение от пользователя {user_id} (причина: {reason}, назначено: {assigned_admin}).")
            return cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении обращения в поддержку: {e}")
            return None

def get_all_support_requests():
    """
    Возвращает все обращения в поддержку (без фильтрации по обработанности).
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM support_requests ORDER BY timestamp DESC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении всех обращений: {e}")
            return []

def get_new_support_requests():
    """
    Возвращает список необработанных (is_processed = 0) обращений.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM support_requests WHERE is_processed = 0 ORDER BY timestamp DESC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении новых обращений: {e}")
            return []

def get_support_requests_for_admin(admin_id=None, reasons=None, include_processed=False):
    """
    Возвращает список обращений для указанного админа, включая не обработанные (is_processed = 0)
    и отложенные (is_processed = 2), с возможностью фильтрации по причинам.
    Если admin_id = None, возвращает обращения без привязки к админу (для главного админа).
    Если include_processed = True, возвращает все обращения (включая обработанные),
    соответствующие фильтрам.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            query_parts = []
            params = []

            if admin_id is not None:
                query_parts.append("assigned_admin = ?")
                params.append(admin_id)

            if not include_processed:
                query_parts.append("is_processed IN (0, 2)") # Необработанные или отложенные

            if reasons:
                placeholders = ','.join(['?']*len(reasons))
                query_parts.append(f"reason IN ({placeholders})")
                params.extend(reasons)

            query = "SELECT * FROM support_requests"
            if query_parts:
                query += " WHERE " + " AND ".join(query_parts)
            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении обращений для админа {admin_id}: {e}")
            return []

def mark_support_request_processed(request_id):
    """
    Помечает обращение как обработанное (is_processed = 1).
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE support_requests SET is_processed = 1 WHERE id = ?", (request_id,))
            conn.commit()
            logging.info(f"Обращение #{request_id} помечено как обработанное.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при пометке обращения #{request_id} как обработанного: {e}")
            conn.rollback()
            return False

def mark_support_request_deferred(request_id):
    """
    Помечает обращение как отложенное (is_processed = 2).
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE support_requests SET is_processed = 2 WHERE id = ?", (request_id,))
            conn.commit()
            logging.info(f"Обращение #{request_id} помечено как отложенное.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при пометке обращения #{request_id} как отложенного: {e}")
            conn.rollback()
            return False

def delete_support_request(request_id):
    """
    Удаляет обращение из базы данных.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM support_requests WHERE id = ?", (request_id,))
            conn.commit()
            logging.info(f"Обращение #{request_id} удалено.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении обращения #{request_id}: {e}")
            conn.rollback()
            return False

def clear_support_requests():
    """
    Удаляет все обращения из базы данных.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM support_requests")
            conn.commit()
            logging.info("Все обращения в поддержку удалены.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке обращений: {e}")
            conn.rollback()
            return False

def assign_admin_to_request(request_id, admin_id):
    """
    Назначает админа на конкретное обращение.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            # Исправлено: условие WHERE assigned_admin IS NULL удалено,
            # чтобы всегда обновлять назначенного админа, если функция вызывается.
            # Если требуется назначение только для NULL, то нужно вернуть условие.
            cursor.execute("UPDATE support_requests SET assigned_admin = ? WHERE id = ?", (admin_id, request_id))
            conn.commit()
            logging.info(f"Обращение #{request_id} назначено админу {admin_id}")
            return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при назначении админа #{admin_id} для обращения #{request_id}: {e}")
            conn.rollback()
            return False

def get_support_request_by_id(request_id):
    """
    Возвращает информацию об обращении по его ID.
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении обращения #{request_id}: {e}")
            return None

# Функции для работы с рассылками (УДАЛЕНЫ)
# def save_broadcast_content(content_type, file_id=None, text_content=None, caption=None):
#     """
#     Сохраняет контент рассылки в базу данных.
#     """
#     with sqlite3.connect("database.db") as conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("INSERT INTO broadcast_content (content_type, file_id, text_content, caption) VALUES (?, ?, ?, ?)",
#                            (content_type, file_id, text_content, caption))
#             conn.commit()
#             logging.info("Контент рассылки сохранён.")
#             return True
#         except sqlite3.Error as e:
#             logging.error(f"Ошибка при сохранении контента рассылки: {e}")
#             return False

# def get_last_broadcast_content():
#     """
#     Возвращает последний сохраненный контент для рассылки.
#     """
#     with sqlite3.connect("database.db") as conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT content_type, file_id, text_content, caption FROM broadcast_content ORDER BY timestamp DESC LIMIT 1")
#             return cursor.fetchone()
#         except sqlite3.Error as e:
#             logging.error(f"Ошибка при получении последнего контента рассылки: {e}")
#             return None

# def clear_broadcast_content():
#     """
#     Удаляет весь сохраненный контент рассылки.
#     """
#     with sqlite3.connect("database.db") as conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("DELETE FROM broadcast_content")
#             conn.commit()
#             logging.info("Весь контент рассылки удален.")
#             return True
#         except sqlite3.Error as e:
#             logging.error(f"Ошибка при очистке контента рассылки: {e}")
#             return False