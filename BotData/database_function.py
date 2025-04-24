import sqlite3
import logging

# Создаём БД и таблицы
def create_tables():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        # Таблица пользователей
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            telegram_id INTEGER UNIQUE,
                            name TEXT,
                            age INTEGER,
                            gender TEXT,
                            university TEXT,
                            description TEXT,
                            photo TEXT
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

        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
        conn.rollback()
    finally:
        conn.close()

# Функция для добавления пользователя в БД
def add_user(telegram_id, name, age, gender, university, description, photo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        cursor.execute('''INSERT INTO users (telegram_id, name, age, gender, university, description, photo)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (telegram_id, name, age, gender, university, description, photo))
        cursor.execute("INSERT INTO location (telegram_id, city) VALUES (?, 'Алматы')", (telegram_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Пользователь {telegram_id} уже зарегистрирован")
        conn.rollback()
        return False
    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении пользователя {telegram_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Функция для поиска пользователей по полу
def get_users_by_gender(gender, exclude_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''SELECT * FROM users 
                          WHERE gender = ? 
                          AND telegram_id != ? 
                          AND telegram_id NOT IN (SELECT to_id FROM likes WHERE from_id = ?)''',
                       (gender, exclude_id, exclude_id))
        users = cursor.fetchall()
        return users
    except sqlite3.Error as e:
        logging.error(f"Ошибка при поиске пользователей по полу {gender}: {e}")
        return []
    finally:
        conn.close()

# Функция для проверки, зарегистрирован ли пользователь
def user_exists(telegram_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        return bool(user)
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке пользователя {telegram_id}: {e}")
        return False
    finally:
        conn.close()

# Функция для добавления лайка
def add_like(from_id, to_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO likes (from_id, to_id) VALUES (?, ?)", (from_id, to_id))
        conn.commit()
    except sqlite3.IntegrityError:
        logging.warning(f"Лайк от {from_id} к {to_id} уже существует")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении лайка {from_id} -> {to_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

# Функция для проверки взаимного лайка
def is_mutual_like(user1, user2):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM likes WHERE from_id = ? AND to_id = ?", (user1, user2))
        like1 = cursor.fetchone()
        cursor.execute("SELECT * FROM likes WHERE from_id = ? AND to_id = ?", (user2, user1))
        like2 = cursor.fetchone()
        return like1 and like2
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке взаимного лайка {user1} <-> {user2}: {e}")
        return False
    finally:
        conn.close()

# Функция для получения данных пользователя по ID
def get_user_by_id(telegram_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
        return None
    finally:
        conn.close()

# Функция для подсчёта лайков пользователя
def count_likes(telegram_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM likes WHERE to_id = ?", (telegram_id,))
        count = cursor.fetchone()[0]
        return count
    except sqlite3.Error as e:
        logging.error(f"Ошибка при подсчёте лайков для {telegram_id}: {e}")
        return 0
    finally:
        conn.close()

# Функция для получения списка пользователей, лайкнувших анкету
def get_likers(telegram_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''SELECT u.* FROM users u
                          JOIN likes l ON u.telegram_id = l.from_id
                          WHERE l.to_id = ?''', (telegram_id,))
        likers = cursor.fetchall()
        return likers
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении списка лайкнувших для {telegram_id}: {e}")
        return []
    finally:
        conn.close()

# Функция для обновления фото пользователя
def update_photo_in_db(telegram_id, photo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET photo = ? WHERE telegram_id = ?", (photo, telegram_id))
        conn.commit()
        logging.info(f"Фото пользователя {telegram_id} успешно обновлено")
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении фото для {telegram_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Функция для обновления описания пользователя
def update_description_in_db(telegram_id, description):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET description = ? WHERE telegram_id = ?", (description, telegram_id))
        conn.commit()
        logging.info(f"Описание пользователя {telegram_id} успешно обновлено")
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении описания для {telegram_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Функция для удаления анкеты одного пользователя
def delete_user(telegram_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        cursor.execute("DELETE FROM location WHERE telegram_id = ?", (telegram_id,))
        cursor.execute("DELETE FROM likes WHERE from_id = ? OR to_id = ?", (telegram_id, telegram_id))
        conn.commit()
        logging.info(f"Анкета пользователя {telegram_id} успешно удалена")
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при удалении анкеты пользователя {telegram_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Функция для удаления всех анкет
def delete_all_profiles():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM location")
        cursor.execute("DELETE FROM likes")
        conn.commit()
        logging.info("Все анкеты успешно удалены")
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при удалении всех анкет: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Создание таблиц при запуске
if __name__ == "__main__":
    create_tables()
    print("База данных успешно настроена!")