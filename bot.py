"""
Telegram-бот миникошелёк для путешественника
"""
import telebot
from telebot import types
from dotenv import load_dotenv
import os
import re
from typing import Optional

from database import Database
from currency_api import get_exchange_rate, convert_currency, check_currency_available
from country_currency import get_currency_by_country, format_currency_name

load_dotenv()

# Инициализация бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# Состояния пользователей для FSM
user_states = {}


def get_user_state(user_id: int) -> dict:
    """Получение состояния пользователя"""
    if user_id not in user_states:
        user_states[user_id] = {}
    return user_states[user_id]


def set_user_state(user_id: int, state: str, data: dict = None):
    """Установка состояния пользователя"""
    user_states[user_id] = {"state": state, "data": data or {}}


def clear_user_state(user_id: int):
    """Очистка состояния пользователя"""
    if user_id in user_states:
        del user_states[user_id]


def format_number(num: float) -> str:
    """Форматирование числа с пробелами для тысяч"""
    return f"{num:,.2f}".replace(",", " ").replace(".", ",")


def create_main_menu() -> types.InlineKeyboardMarkup:
    """Создание главного меню"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✈️ Создать путешествие", callback_data="new_trip"),
        types.InlineKeyboardButton("📋 Мои путешествия", callback_data="my_trips")
    )
    keyboard.add(
        types.InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        types.InlineKeyboardButton("📊 История расходов", callback_data="history")
    )
    keyboard.add(
        types.InlineKeyboardButton("💱 Изменить курс", callback_data="change_rate")
    )
    return keyboard


def send_main_menu(chat_id: int, text: str = "🏠 Главное меню"):
    """Отправка главного меню"""
    bot.send_message(chat_id, text, reply_markup=create_main_menu())


@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    db.add_user(user_id, username)
    clear_user_state(user_id)
    
    welcome_text = (
        "👋 Добро пожаловать в миникошелёк для путешественника!\n\n"
        "Я помогу вам отслеживать расходы во время путешествий и конвертировать валюты.\n\n"
        "Используйте меню ниже или команды:\n"
        "/newtrip - создать новое путешествие\n"
        "/switch - переключить путешествие\n"
        "/balance - показать баланс\n"
        "/history - история расходов\n"
        "/setrate - изменить курс обмена"
    )
    
    send_main_menu(message.chat.id, welcome_text)


@bot.message_handler(commands=['newtrip', 'switch', 'balance', 'history', 'setrate'])
def handle_commands(message):
    """Обработка команд меню"""
    command = message.text.split()[0][1:]  # Убираем /
    
    if command == "newtrip":
        start_new_trip(message)
    elif command == "switch":
        show_trips_list(message)
    elif command == "balance":
        show_balance(message)
    elif command == "history":
        show_history(message)
    elif command == "setrate":
        start_change_rate(message)


@bot.callback_query_handler(func=lambda call: call.data == "new_trip")
def callback_new_trip(call):
    """Обработка нажатия на кнопку создания путешествия"""
    user_id = call.from_user.id
    set_user_state(user_id, "waiting_from_country")
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "✈️ Создание нового путешествия\n\n"
        "Введите страну отправления (например: Россия, Russia, RU):"
    )


def start_new_trip(message):
    """Начало создания нового путешествия"""
    if not hasattr(message, 'from_user') or not message.from_user:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не удалось определить пользователя."
        )
        return
    
    user_id = message.from_user.id
    set_user_state(user_id, "waiting_from_country")
    bot.send_message(
        message.chat.id,
        "✈️ Создание нового путешествия\n\n"
        "Введите страну отправления (например: Россия, Russia, RU):"
    )


@bot.callback_query_handler(func=lambda call: call.data == "my_trips")
def callback_my_trips(call):
    """Обработка нажатия на кнопку 'Мои путешествия'"""
    user_id = call.from_user.id
    trips = db.get_user_trips(user_id)
    
    if not trips:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "📋 У вас пока нет путешествий.\n\n"
            "Создайте новое путешествие через меню или команду /newtrip",
            reply_markup=create_main_menu()
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        button_text = f"{active_mark}{trip['name']} ({trip['from_country']} → {trip['to_country']})"
        keyboard.add(types.InlineKeyboardButton(
            button_text,
            callback_data=f"switch_trip_{trip['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    trips_text = "📋 Ваши путешествия:\n\n"
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        trips_text += f"{active_mark}{trip['name']}\n"
        trips_text += f"   {trip['from_country']} ({trip['from_currency']}) → "
        trips_text += f"{trip['to_country']} ({trip['to_currency']})\n"
        trips_text += f"   Курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}\n\n"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, trips_text, reply_markup=keyboard)


def show_trips_list(message):
    """Показать список путешествий пользователя"""
    if not hasattr(message, 'from_user') or not message.from_user:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не удалось определить пользователя."
        )
        return
    
    user_id = message.from_user.id
    
    trips = db.get_user_trips(user_id)
    
    if not trips:
        bot.send_message(
            message.chat.id,
            "📋 У вас пока нет путешествий.\n\n"
            "Создайте новое путешествие через меню или команду /newtrip",
            reply_markup=create_main_menu()
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        button_text = f"{active_mark}{trip['name']} ({trip['from_country']} → {trip['to_country']})"
        keyboard.add(types.InlineKeyboardButton(
            button_text,
            callback_data=f"switch_trip_{trip['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    trips_text = "📋 Ваши путешествия:\n\n"
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        trips_text += f"{active_mark}{trip['name']}\n"
        trips_text += f"   {trip['from_country']} ({trip['from_currency']}) → "
        trips_text += f"{trip['to_country']} ({trip['to_currency']})\n"
        trips_text += f"   Курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}\n\n"
    
    bot.send_message(message.chat.id, trips_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("switch_trip_"))
def callback_switch_trip(call):
    """Переключение активного путешествия"""
    user_id = call.from_user.id
    trip_id = int(call.data.split("_")[2])
    
    db.switch_trip(user_id, trip_id)
    bot.answer_callback_query(call.id, "✅ Путешествие активировано!")
    
    # Показываем обновленный список путешествий
    trips = db.get_user_trips(user_id)
    
    if not trips:
        bot.send_message(
            call.message.chat.id,
            "📋 У вас пока нет путешествий.\n\n"
            "Создайте новое путешествие через меню или команду /newtrip",
            reply_markup=create_main_menu()
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        button_text = f"{active_mark}{trip['name']} ({trip['from_country']} → {trip['to_country']})"
        keyboard.add(types.InlineKeyboardButton(
            button_text,
            callback_data=f"switch_trip_{trip['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    trips_text = "📋 Ваши путешествия:\n\n"
    for trip in trips:
        active_mark = "✅ " if trip['is_active'] else ""
        trips_text += f"{active_mark}{trip['name']}\n"
        trips_text += f"   {trip['from_country']} ({trip['from_currency']}) → "
        trips_text += f"{trip['to_country']} ({trip['to_currency']})\n"
        trips_text += f"   Курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}\n\n"
    
    bot.send_message(call.message.chat.id, trips_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "balance")
def callback_balance(call):
    """Обработка нажатия на кнопку 'Баланс'"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "❌ У вас нет активного путешествия.\n\n"
            "Создайте новое путешествие или выберите существующее.",
            reply_markup=create_main_menu()
        )
        return
    
    balance_text = (
        f"💰 Баланс путешествия: {trip['name']}\n\n"
        f"📍 {trip['from_country']} ({trip['from_currency']}) → "
        f"{trip['to_country']} ({trip['to_currency']})\n\n"
        f"💵 Остаток:\n"
        f"   {format_number(trip['balance_to'])} {trip['to_currency']} = "
        f"{format_number(trip['balance_from'])} {trip['from_currency']}\n\n"
        f"💱 Курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, balance_text, reply_markup=keyboard)


def show_balance(message):
    """Показать баланс активного путешествия"""
    if not hasattr(message, 'from_user') or not message.from_user:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не удалось определить пользователя."
        )
        return
    
    user_id = message.from_user.id
    
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активного путешествия.\n\n"
            "Создайте новое путешествие или выберите существующее.",
            reply_markup=create_main_menu()
        )
        return
    
    balance_text = (
        f"💰 Баланс путешествия: {trip['name']}\n\n"
        f"📍 {trip['from_country']} ({trip['from_currency']}) → "
        f"{trip['to_country']} ({trip['to_currency']})\n\n"
        f"💵 Остаток:\n"
        f"   {format_number(trip['balance_to'])} {trip['to_currency']} = "
        f"{format_number(trip['balance_from'])} {trip['from_currency']}\n\n"
        f"💱 Курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(message.chat.id, balance_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "history")
def callback_history(call):
    """Обработка нажатия на кнопку 'История расходов'"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "❌ У вас нет активного путешествия.",
            reply_markup=create_main_menu()
        )
        return
    
    expenses = db.get_expenses(trip['id'], limit=20)
    
    if not expenses:
        history_text = (
            f"📊 История расходов: {trip['name']}\n\n"
            "Пока нет расходов."
        )
    else:
        history_text = f"📊 История расходов: {trip['name']}\n\n"
        total_to = 0
        total_from = 0
        
        for expense in expenses:
            total_to += expense['amount_to']
            total_from += expense['amount_from']
            
            # Форматируем дату и время
            if expense['created_at']:
                dt_str = expense['created_at']
                if len(dt_str) >= 16:
                    date_part = dt_str[:10]  # 2026-02-05
                    time_part = dt_str[11:16]  # 16:06
                    # Преобразуем дату из формата YYYY-MM-DD в DD.MM.YYYY
                    date_parts = date_part.split('-')
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0]}"
                        datetime_str = f"{formatted_date} {time_part}"
                    else:
                        datetime_str = dt_str[:16]
                else:
                    datetime_str = dt_str[:10] if len(dt_str) >= 10 else dt_str
            else:
                datetime_str = ""
            
            desc = expense['description'] or ""
            history_text += (
                f"📅 {datetime_str}\n"
                f"   {format_number(expense['amount_to'])} {trip['to_currency']} = "
                f"{format_number(expense['amount_from'])} {trip['from_currency']}\n"
            )
            if desc:
                history_text += f"   💬 {desc}\n"
            history_text += "\n"
        
        history_text += (
            f"\n📊 Всего потрачено:\n"
            f"   {format_number(total_to)} {trip['to_currency']} = "
            f"{format_number(total_from)} {trip['from_currency']}"
        )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, history_text, reply_markup=keyboard)


def show_history(message):
    """Показать историю расходов"""
    if not hasattr(message, 'from_user') or not message.from_user:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не удалось определить пользователя."
        )
        return
    
    user_id = message.from_user.id
    
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активного путешествия.",
            reply_markup=create_main_menu()
        )
        return
    
    expenses = db.get_expenses(trip['id'], limit=20)
    
    if not expenses:
        history_text = (
            f"📊 История расходов: {trip['name']}\n\n"
            "Пока нет расходов."
        )
    else:
        history_text = f"📊 История расходов: {trip['name']}\n\n"
        total_to = 0
        total_from = 0
        
        for expense in expenses:
            total_to += expense['amount_to']
            total_from += expense['amount_from']
            
            # Форматируем дату и время
            if expense['created_at']:
                dt_str = expense['created_at']
                if len(dt_str) >= 16:
                    date_part = dt_str[:10]  # 2026-02-05
                    time_part = dt_str[11:16]  # 16:06
                    # Преобразуем дату из формата YYYY-MM-DD в DD.MM.YYYY
                    date_parts = date_part.split('-')
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0]}"
                        datetime_str = f"{formatted_date} {time_part}"
                    else:
                        datetime_str = dt_str[:16]
                else:
                    datetime_str = dt_str[:10] if len(dt_str) >= 10 else dt_str
            else:
                datetime_str = ""
            
            desc = expense['description'] or ""
            history_text += (
                f"📅 {datetime_str}\n"
                f"   {format_number(expense['amount_to'])} {trip['to_currency']} = "
                f"{format_number(expense['amount_from'])} {trip['from_currency']}\n"
            )
            if desc:
                history_text += f"   💬 {desc}\n"
            history_text += "\n"
        
        history_text += (
            f"\n📊 Всего потрачено:\n"
            f"   {format_number(total_to)} {trip['to_currency']} = "
            f"{format_number(total_from)} {trip['from_currency']}"
        )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(message.chat.id, history_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "change_rate")
def callback_change_rate(call):
    """Обработка нажатия на кнопку 'Изменить курс'"""
    user_id = call.from_user.id
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "❌ У вас нет активного путешествия.",
            reply_markup=create_main_menu()
        )
        return
    
    set_user_state(user_id, "waiting_new_rate", {"trip_id": trip['id']})
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"💱 Изменение курса для путешествия: {trip['name']}\n\n"
        f"Текущий курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}\n\n"
        f"Введите новый курс обмена (сколько {trip['to_currency']} за 1 {trip['from_currency']}):"
    )


def start_change_rate(message):
    """Начало изменения курса"""
    if not hasattr(message, 'from_user') or not message.from_user:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не удалось определить пользователя."
        )
        return
    
    user_id = message.from_user.id
    
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активного путешествия.",
            reply_markup=create_main_menu()
        )
        return
    
    set_user_state(user_id, "waiting_new_rate", {"trip_id": trip['id']})
    
    bot.send_message(
        message.chat.id,
        f"💱 Изменение курса для путешествия: {trip['name']}\n\n"
        f"Текущий курс: 1 {trip['from_currency']} = {format_number(trip['exchange_rate'])} {trip['to_currency']}\n\n"
        f"Введите новый курс обмена (сколько {trip['to_currency']} за 1 {trip['from_currency']}):"
    )


@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def callback_main_menu(call):
    """Обработка нажатия на кнопку 'Главное меню'"""
    send_main_menu(call.message.chat.id)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработка всех текстовых сообщений"""
    # Получаем user_id с проверкой
    if not hasattr(message, 'from_user') or not message.from_user:
        return
    
    user_id = message.from_user.id
    text = message.text.strip()
    
    state_data = get_user_state(user_id)
    state = state_data.get("state")
    
    # Проверяем команду /skip для пропуска наименования расхода
    if text.lower() == "/skip":
        if state == "waiting_expense_description":
            handle_expense_description(message, text)
        return
    
    # Проверяем, не является ли это командой (команды обрабатываются отдельно)
    if text.startswith('/'):
        return
    
    # Если пользователь в процессе создания путешествия
    if state == "waiting_from_country":
        handle_from_country(message, text)
        return
    elif state == "waiting_to_country":
        handle_to_country(message, text)
        return
    elif state == "waiting_rate_confirmation":
        # Это обрабатывается через callback
        return
    elif state == "waiting_manual_rate":
        handle_manual_rate(message, text)
        return
    elif state == "waiting_initial_amount":
        handle_initial_amount(message, text)
        return
    elif state == "waiting_new_rate":
        handle_new_rate(message, text)
        return
    elif state == "waiting_expense_confirmation":
        # Это обрабатывается через callback
        return
    elif state == "waiting_expense_description":
        handle_expense_description(message, text)
        return
    
    # Если состояние не установлено, проверяем, является ли сообщение числом (расход)
    if is_number(text):
        handle_expense_input(message, float(text.replace(",", ".")))
    else:
        # Неизвестная команда или текст
        send_main_menu(message.chat.id, "❓ Не понимаю команду. Используйте меню ниже:")


def is_number(text: str) -> bool:
    """Проверка, является ли текст числом"""
    try:
        # Заменяем запятую на точку для русской локали
        text = text.replace(",", ".").replace(" ", "")
        float(text)
        return True
    except ValueError:
        return False


def handle_from_country(message, country_name: str):
    """Обработка ввода страны отправления"""
    if not hasattr(message, 'from_user') or not message.from_user:
        return
    
    user_id = message.from_user.id
    # Нормализуем ввод: убираем лишние пробелы и приводим к нижнему регистру для поиска
    country_normalized = country_name.strip()
    currency = get_currency_by_country(country_normalized)
    
    if not currency:
        bot.send_message(
            message.chat.id,
            f"❌ Не удалось определить валюту для страны '{country_name}'.\n\n"
            "Пожалуйста, введите название страны ещё раз (например: Россия, Russia, RU):"
        )
        return
    
    set_user_state(user_id, "waiting_to_country", {
        "from_country": country_normalized,
        "from_currency": currency
    })
    
    bot.send_message(
        message.chat.id,
        f"✅ Страна отправления: {country_normalized} ({currency})\n\n"
        "Введите страну назначения (например: Китай, China, CN):"
    )


def handle_to_country(message, country_name: str):
    """Обработка ввода страны назначения"""
    if not hasattr(message, 'from_user') or not message.from_user:
        return
    
    user_id = message.from_user.id
    state_data = get_user_state(user_id)
    data = state_data.get("data", {})
    from_country = data.get("from_country")
    from_currency = data.get("from_currency")
    
    if not from_country or not from_currency:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка состояния. Начните создание путешествия заново.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    
    # Нормализуем ввод
    country_normalized = country_name.strip()
    currency = get_currency_by_country(country_normalized)
    
    if not currency:
        bot.send_message(
            message.chat.id,
            f"❌ Не удалось определить валюту для страны '{country_normalized}'.\n\n"
            "Пожалуйста, введите название страны ещё раз:"
        )
        return
    
    if currency == from_currency:
        bot.send_message(
            message.chat.id,
            "❌ Валюты стран отправления и назначения совпадают.\n\n"
            "Введите другую страну назначения:"
        )
        return
    
    to_currency = currency
    
    # Проверяем доступность валют в API
    if not check_currency_available(from_currency):
        bot.send_message(
            message.chat.id,
            f"❌ Валюта {from_currency} недоступна в API.\n\n"
            "Пожалуйста, начните создание путешествия заново.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    
    if not check_currency_available(to_currency):
        bot.send_message(
            message.chat.id,
            f"❌ Валюта {to_currency} недоступна в API.\n\n"
            "Пожалуйста, введите другую страну назначения:"
        )
        return
    
    # Получаем курс обмена
    rate_data = get_exchange_rate(from_currency, to_currency)
    
    if not rate_data or not rate_data.get("success"):
        error_msg = rate_data.get("error", "Неизвестная ошибка") if rate_data else "Ошибка запроса"
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка при получении курса обмена: {error_msg}\n\n"
            "Пожалуйста, попробуйте позже или начните заново.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    
    rate = rate_data["rate"]
    
    # Сохраняем данные и запрашиваем подтверждение курса
    set_user_state(user_id, "waiting_rate_confirmation", {
        "from_country": from_country,
        "to_country": country_normalized,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate
    })
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Да", callback_data="rate_yes"),
        types.InlineKeyboardButton("❌ Нет", callback_data="rate_no")
    )
    
    bot.send_message(
        message.chat.id,
        f"💱 Курс обмена:\n\n"
        f"1 {from_currency} = {format_number(rate)} {to_currency}\n\n"
        f"Подходит ли этот курс?",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "rate_yes")
def callback_rate_yes(call):
    """Подтверждение курса"""
    user_id = call.from_user.id
    state_data = get_user_state(user_id)
    
    if state_data.get("state") != "waiting_rate_confirmation":
        bot.answer_callback_query(call.id, "❌ Ошибка состояния")
        return
    
    data = state_data.get("data", {})
    if not data:
        bot.answer_callback_query(call.id, "❌ Ошибка данных")
        return
    
    # Переходим к запросу начальной суммы
    set_user_state(user_id, "waiting_initial_amount", data)
    
    bot.edit_message_text(
        f"✅ Курс подтверждён!\n\n"
        f"Введите начальную сумму в {format_currency_name(data['from_currency'])}:",
        call.message.chat.id,
        call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "rate_no")
def callback_rate_no(call):
    """Отказ от курса, запрос ручного ввода"""
    user_id = call.from_user.id
    state_data = get_user_state(user_id)
    
    if state_data.get("state") != "waiting_rate_confirmation":
        bot.answer_callback_query(call.id, "❌ Ошибка состояния")
        return
    
    data = state_data.get("data", {})
    if not data:
        bot.answer_callback_query(call.id, "❌ Ошибка данных")
        return
    set_user_state(user_id, "waiting_manual_rate", data)
    
    bot.edit_message_text(
        f"Введите курс обмена вручную:\n"
        f"Сколько {data['to_currency']} за 1 {data['from_currency']}?",
        call.message.chat.id,
        call.message.message_id
    )


def handle_manual_rate(message, rate_text: str):
    """Обработка ручного ввода курса"""
    user_id = message.from_user.id
    
    if not is_number(rate_text):
        bot.send_message(
            message.chat.id,
            "❌ Пожалуйста, введите число (например: 12.5 или 12,5):"
        )
        return
    
    rate = float(rate_text.replace(",", "."))
    
    if rate <= 0:
        bot.send_message(
            message.chat.id,
            "❌ Курс должен быть положительным числом. Введите ещё раз:"
        )
        return
    
    state_data = get_user_state(user_id)
    state_data["data"]["rate"] = rate
    set_user_state(user_id, "waiting_initial_amount", state_data["data"])
    
    bot.send_message(
        message.chat.id,
        f"✅ Курс установлен: 1 {state_data['data']['from_currency']} = {format_number(rate)} {state_data['data']['to_currency']}\n\n"
        f"Введите начальную сумму в {format_currency_name(state_data['data']['from_currency'])}:"
    )


def handle_initial_amount(message, amount_text: str):
    """Обработка ввода начальной суммы"""
    user_id = message.from_user.id
    
    if not is_number(amount_text):
        bot.send_message(
            message.chat.id,
            "❌ Пожалуйста, введите число (например: 1000 или 1000,50):"
        )
        return
    
    amount_from = float(amount_text.replace(",", "."))
    
    if amount_from <= 0:
        bot.send_message(
            message.chat.id,
            "❌ Сумма должна быть положительным числом. Введите ещё раз:"
        )
        return
    
    state_data = get_user_state(user_id)
    data = state_data.get("data", {})
    
    if not data or "from_currency" not in data or "to_currency" not in data:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка состояния. Начните создание путешествия заново.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    
    rate = data.get("rate", 1.0)
    
    # Конвертируем через API для точности
    conversion = convert_currency(amount_from, data["from_currency"], data["to_currency"])
    
    if not conversion or not conversion.get("success"):
        # Используем сохранённый курс, если API недоступен
        amount_to = amount_from * rate
        bot.send_message(
            message.chat.id,
            "⚠️ Не удалось получить актуальный курс через API. Используется сохранённый курс."
        )
    else:
        amount_to = conversion["converted_amount"]
        # Обновляем курс на актуальный из API
        rate = conversion["rate"]
        data["rate"] = rate
    
    # Создаём название путешествия
    trip_name = f"{data['from_country']} → {data['to_country']}"
    
    # Создаём путешествие в БД
    trip_id = db.create_trip(
        user_id=user_id,
        name=trip_name,
        from_country=data["from_country"],
        to_country=data["to_country"],
        from_currency=data["from_currency"],
        to_currency=data["to_currency"],
        exchange_rate=rate,
        initial_amount_from=amount_from,
        initial_amount_to=amount_to
    )
    
    clear_user_state(user_id)
    
    success_text = (
        f"✅ Путешествие создано!\n\n"
        f"📍 {trip_name}\n"
        f"💱 Курс: 1 {data['from_currency']} = {format_number(rate)} {data['to_currency']}\n\n"
        f"💰 Начальный баланс:\n"
        f"   {format_number(amount_to)} {data['to_currency']} = "
        f"{format_number(amount_from)} {data['from_currency']}\n\n"
        f"Теперь вы можете вводить суммы расходов, и я буду их конвертировать!"
    )
    
    send_main_menu(message.chat.id, success_text)


def handle_expense_input(message, amount: float):
    """Обработка ввода суммы расхода"""
    user_id = message.from_user.id
    
    if amount <= 0:
        send_main_menu(message.chat.id, "❌ Сумма должна быть положительным числом.")
        return
    
    trip = db.get_active_trip(user_id)
    
    if not trip:
        send_main_menu(
            message.chat.id,
            "❌ У вас нет активного путешествия.\n\n"
            "Создайте новое путешествие или выберите существующее."
        )
        return
    
    # Конвертируем расход в домашнюю валюту используя курс из базы данных
    # Курс хранится как: сколько to_currency за 1 from_currency
    # Для обратной конвертации (to_currency -> from_currency) нужно делить на курс
    rate = trip['exchange_rate']
    amount_from = amount / rate  # Обратная конвертация: amount_to / rate = amount_from
    
    # Сохраняем данные для подтверждения
    set_user_state(user_id, "waiting_expense_confirmation", {
        "trip_id": trip['id'],
        "amount_to": amount,
        "amount_from": amount_from
    })
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Да", callback_data="expense_yes"),
        types.InlineKeyboardButton("❌ Нет", callback_data="expense_no")
    )
    
    bot.send_message(
        message.chat.id,
        f"💵 {format_number(amount)} {trip['to_currency']} = "
        f"{format_number(amount_from)} {trip['from_currency']}\n\n"
        f"Учесть как расход?",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "expense_yes")
def callback_expense_yes(call):
    """Подтверждение расхода"""
    user_id = call.from_user.id
    state_data = get_user_state(user_id)
    
    if state_data.get("state") != "waiting_expense_confirmation":
        bot.answer_callback_query(call.id, "❌ Ошибка состояния")
        return
    
    data = state_data.get("data", {})
    if not data or "trip_id" not in data:
        bot.answer_callback_query(call.id, "❌ Ошибка данных")
        return
    
    # Добавляем расход
    expense_id = db.add_expense(
        trip_id=data["trip_id"],
        amount_to=data["amount_to"],
        amount_from=data["amount_from"]
    )
    
    # Получаем обновлённый баланс
    trip = db.get_active_trip(user_id)
    
    if not trip:
        bot.edit_message_text(
            "❌ Ошибка: путешествие не найдено",
            call.message.chat.id,
            call.message.message_id
        )
        clear_user_state(user_id)
        return
    
    # Переходим в состояние ожидания наименования расхода
    set_user_state(user_id, "waiting_expense_description", {
        "expense_id": expense_id,
        "trip_id": data["trip_id"]
    })
    
    bot.edit_message_text(
        f"✅ Расход учтён!\n\n"
        f"💰 Остаток:\n"
        f"   {format_number(trip['balance_to'])} {trip['to_currency']} = "
        f"{format_number(trip['balance_from'])} {trip['from_currency']}\n\n"
        f"💬 Введите наименование расхода (или отправьте /skip чтобы пропустить):",
        call.message.chat.id,
        call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "expense_no")
def callback_expense_no(call):
    """Отмена расхода"""
    user_id = call.from_user.id
    clear_user_state(user_id)
    
    bot.edit_message_text(
        "❌ Расход не учтён.",
        call.message.chat.id,
        call.message.message_id
    )


def handle_expense_description(message, description: str):
    """Обработка ввода наименования расхода"""
    user_id = message.from_user.id
    state_data = get_user_state(user_id)
    
    # Проверяем команду /skip
    if description.strip().lower() == "/skip":
        clear_user_state(user_id)
        bot.send_message(
            message.chat.id,
            "✅ Расход сохранён без наименования.",
            reply_markup=create_main_menu()
        )
        return
    
    data = state_data.get("data", {})
    expense_id = data.get("expense_id")
    
    if not expense_id:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: не найден ID расхода.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    
    # Обновляем наименование расхода
    db.update_expense_description(expense_id, description.strip())
    
    clear_user_state(user_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ Наименование расхода сохранено: {description.strip()}",
        reply_markup=create_main_menu()
    )


def handle_new_rate(message, rate_text: str):
    """Обработка нового курса"""
    user_id = message.from_user.id
    state_data = get_user_state(user_id)
    
    if not is_number(rate_text):
        bot.send_message(
            message.chat.id,
            "❌ Пожалуйста, введите число (например: 12.5 или 12,5):"
        )
        return
    
    rate = float(rate_text.replace(",", "."))
    
    if rate <= 0:
        bot.send_message(
            message.chat.id,
            "❌ Курс должен быть положительным числом. Введите ещё раз:"
        )
        return
    
    data = state_data.get("data", {})
    trip_id = data.get("trip_id")
    
    if not trip_id:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка состояния. Начните изменение курса заново.",
            reply_markup=create_main_menu()
        )
        clear_user_state(user_id)
        return
    db.update_exchange_rate(trip_id, rate)
    
    clear_user_state(user_id)
    
    trip = db.get_active_trip(user_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ Курс обновлён!\n\n"
        f"Новый курс: 1 {trip['from_currency']} = {format_number(rate)} {trip['to_currency']}\n\n"
        f"💰 Баланс пересчитан:\n"
        f"   {format_number(trip['balance_to'])} {trip['to_currency']} = "
        f"{format_number(trip['balance_from'])} {trip['from_currency']}",
        reply_markup=create_main_menu()
    )


if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.infinity_polling(none_stop=True)
