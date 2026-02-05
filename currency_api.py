"""
Модуль для работы с API exchangerate.host
Использует функции из current_api.py
"""
import requests
from dotenv import load_dotenv
import os
from typing import Optional, Dict

load_dotenv()
API_KEY = os.getenv("CURRENCY_API_KEY")


def get_exchange_rate(source_currency: str, target_currency: str) -> Optional[Dict]:
    """
    Получение курса обмена между двумя валютами через api.exchangerate.host
    
    Args:
        source_currency: Исходная валюта (например, "RUB")
        target_currency: Целевая валюта (например, "CNY")
    
    Returns:
        Словарь с данными курса или None в случае ошибки
    """
    url = "https://api.exchangerate.host/live"
    params = {
        "access_key": API_KEY,
        "source": source_currency,
        "currencies": target_currency
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Проверяем успешность запроса
        if data.get("success") is False:
            error_info = data.get("error", {})
            return {
                "success": False,
                "error": error_info.get("info", "Unknown error")
            }
        
        # Извлекаем курс из ответа
        quotes = data.get("quotes", {})
        rate_key = f"{source_currency}{target_currency}"
        
        if rate_key in quotes:
            return {
                "success": True,
                "rate": quotes[rate_key],
                "source": source_currency,
                "target": target_currency
            }
        else:
            return {
                "success": False,
                "error": f"Currency pair {source_currency}/{target_currency} not found"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def convert_currency(amount: float, source_currency: str, target_currency: str) -> Optional[Dict]:
    """
    Конвертация суммы из одной валюты в другую
    
    Args:
        amount: Сумма для конвертации
        source_currency: Исходная валюта
        target_currency: Целевая валюта
    
    Returns:
        Словарь с результатом конвертации или None в случае ошибки
    """
    rate_data = get_exchange_rate(source_currency, target_currency)
    
    if not rate_data or not rate_data.get("success"):
        return rate_data
    
    rate = rate_data["rate"]
    converted_amount = amount * rate
    
    return {
        "success": True,
        "amount": amount,
        "converted_amount": converted_amount,
        "rate": rate,
        "source": source_currency,
        "target": target_currency
    }


def check_currency_available(currency: str) -> bool:
    """
    Проверка доступности валюты в API
    
    Args:
        currency: Код валюты для проверки
    
    Returns:
        True если валюта доступна, False иначе
    """
    # Проверяем через запрос к USD (базовая валюта обычно доступна)
    result = get_exchange_rate("USD", currency)
    if result and result.get("success"):
        return True
    
    # Пробуем обратный запрос
    result = get_exchange_rate(currency, "USD")
    return result and result.get("success")
