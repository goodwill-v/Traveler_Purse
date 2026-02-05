import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple

DB_PATH = "travel_wallet.db"


class Database:
    def __init__(self):
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        """Инициализация базы данных с созданием таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица путешествий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                from_country TEXT NOT NULL,
                to_country TEXT NOT NULL,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                exchange_rate REAL NOT NULL,
                balance_from REAL NOT NULL DEFAULT 0,
                balance_to REAL NOT NULL DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица расходов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                amount_to REAL NOT NULL,
                amount_from REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trip_id) REFERENCES trips(id)
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: Optional[str] = None):
        """Добавление пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            conn.commit()
        finally:
            conn.close()

    def create_trip(self, user_id: int, name: str, from_country: str, to_country: str,
                    from_currency: str, to_currency: str, exchange_rate: float,
                    initial_amount_from: float, initial_amount_to: float) -> int:
        """Создание нового путешествия"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Деактивируем все другие путешествия пользователя
        cursor.execute(
            "UPDATE trips SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )

        # Создаём новое путешествие
        cursor.execute("""
            INSERT INTO trips (user_id, name, from_country, to_country, 
                             from_currency, to_currency, exchange_rate,
                             balance_from, balance_to, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, name, from_country, to_country, from_currency,
              to_currency, exchange_rate, initial_amount_from, initial_amount_to))

        trip_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trip_id

    def get_active_trip(self, user_id: int) -> Optional[Dict]:
        """Получение активного путешествия пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, from_country, to_country, from_currency, 
                   to_currency, exchange_rate, balance_from, balance_to
            FROM trips
            WHERE user_id = ? AND is_active = 1
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'name': row[1],
                'from_country': row[2],
                'to_country': row[3],
                'from_currency': row[4],
                'to_currency': row[5],
                'exchange_rate': row[6],
                'balance_from': row[7],
                'balance_to': row[8]
            }
        return None

    def get_user_trips(self, user_id: int) -> List[Dict]:
        """Получение всех путешествий пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, from_country, to_country, from_currency, 
                   to_currency, exchange_rate, balance_from, balance_to, is_active
            FROM trips
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': row[0],
            'name': row[1],
            'from_country': row[2],
            'to_country': row[3],
            'from_currency': row[4],
            'to_currency': row[5],
            'exchange_rate': row[6],
            'balance_from': row[7],
            'balance_to': row[8],
            'is_active': row[9]
        } for row in rows]

    def switch_trip(self, user_id: int, trip_id: int):
        """Переключение активного путешествия"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Деактивируем все путешествия пользователя
        cursor.execute("UPDATE trips SET is_active = 0 WHERE user_id = ?", (user_id,))
        # Активируем выбранное
        cursor.execute("UPDATE trips SET is_active = 1 WHERE id = ? AND user_id = ?",
                      (trip_id, user_id))
        conn.commit()
        conn.close()

    def add_expense(self, trip_id: int, amount_to: float, amount_from: float,
                   description: Optional[str] = None):
        """Добавление расхода и обновление баланса"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Добавляем расход
        cursor.execute("""
            INSERT INTO expenses (trip_id, amount_to, amount_from, description)
            VALUES (?, ?, ?, ?)
        """, (trip_id, amount_to, amount_from, description))

        expense_id = cursor.lastrowid

        # Обновляем баланс
        cursor.execute("""
            UPDATE trips
            SET balance_to = balance_to - ?,
                balance_from = balance_from - ?
            WHERE id = ?
        """, (amount_to, amount_from, trip_id))

        conn.commit()
        conn.close()
        return expense_id

    def update_expense_description(self, expense_id: int, description: str):
        """Обновление наименования расхода"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE expenses
            SET description = ?
            WHERE id = ?
        """, (description, expense_id))
        conn.commit()
        conn.close()

    def get_expenses(self, trip_id: int, limit: int = 10) -> List[Dict]:
        """Получение истории расходов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT amount_to, amount_from, description, created_at
            FROM expenses
            WHERE trip_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (trip_id, limit))
        rows = cursor.fetchall()
        conn.close()

        return [{
            'amount_to': row[0],
            'amount_from': row[1],
            'description': row[2],
            'created_at': row[3]
        } for row in rows]

    def update_exchange_rate(self, trip_id: int, new_rate: float):
        """Обновление курса обмена для путешествия
        
        Курс хранится как: сколько to_currency за 1 from_currency
        Для обратной конвертации (to_currency -> from_currency) нужно делить на курс
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем текущий баланс в валюте назначения
        cursor.execute("SELECT balance_to FROM trips WHERE id = ?", (trip_id,))
        balance_to = cursor.fetchone()[0]

        # Пересчитываем баланс в домашней валюте с новым курсом
        # Курс: сколько to_currency за 1 from_currency
        # Для конвертации to_currency -> from_currency: делим на курс
        new_balance_from = balance_to / new_rate

        cursor.execute("""
            UPDATE trips
            SET exchange_rate = ?,
                balance_from = ?
            WHERE id = ?
        """, (new_rate, new_balance_from, trip_id))

        conn.commit()
        conn.close()
