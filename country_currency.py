"""
Маппинг стран к валютам для определения валюты по названию страны
"""

COUNTRY_CURRENCY_MAP = {
    # Европа
    "россия": "RUB", "russia": "RUB", "ru": "RUB",
    "украина": "UAH", "ukraine": "UAH", "ua": "UAH",
    "беларусь": "BYN", "belarus": "BYN", "by": "BYN",
    "польша": "PLN", "poland": "PLN", "pl": "PLN",
    "германия": "EUR", "germany": "EUR", "de": "EUR",
    "франция": "EUR", "france": "EUR", "fr": "EUR",
    "италия": "EUR", "italy": "EUR", "it": "EUR",
    "испания": "EUR", "spain": "EUR", "es": "EUR",
    "великобритания": "GBP", "united kingdom": "GBP", "uk": "GBP", "britain": "GBP",
    "нидерланды": "EUR", "netherlands": "EUR", "nl": "EUR",
    "бельгия": "EUR", "belgium": "EUR", "be": "EUR",
    "австрия": "EUR", "austria": "EUR", "at": "EUR",
    "швейцария": "CHF", "switzerland": "CHF", "ch": "CHF",
    "швеция": "SEK", "sweden": "SEK", "se": "SEK",
    "норвегия": "NOK", "norway": "NOK", "no": "NOK",
    "дания": "DKK", "denmark": "DKK", "dk": "DKK",
    "финляндия": "EUR", "finland": "EUR", "fi": "EUR",
    "чехия": "CZK", "czech republic": "CZK", "cz": "CZK",
    "венгрия": "HUF", "hungary": "HUF", "hu": "HUF",
    "румыния": "RON", "romania": "RON", "ro": "RON",
    "греция": "EUR", "greece": "EUR", "gr": "EUR",
    "португалия": "EUR", "portugal": "EUR", "pt": "EUR",
    "турция": "TRY", "turkey": "TRY", "tr": "TRY",
    
    # Азия
    "китай": "CNY", "china": "CNY", "cn": "CNY",
    "япония": "JPY", "japan": "JPY", "jp": "JPY",
    "южная корея": "KRW", "south korea": "KRW", "korea": "KRW", "kr": "KRW",
    "индия": "INR", "india": "INR", "in": "INR",
    "тайланд": "THB", "thailand": "THB", "th": "THB",
    "вьетнам": "VND", "vietnam": "VND", "vn": "VND",
    "индонезия": "IDR", "indonesia": "IDR", "id": "IDR",
    "малайзия": "MYR", "malaysia": "MYR", "my": "MYR",
    "сингапур": "SGD", "singapore": "SGD", "sg": "SGD",
    "филиппины": "PHP", "philippines": "PHP", "ph": "PHP",
    "израиль": "ILS", "israel": "ILS", "il": "ILS",
    "оаэ": "AED", "united arab emirates": "AED", "uae": "AED", "ae": "AED",
    "саудовская аравия": "SAR", "saudi arabia": "SAR", "sa": "SAR",
    "казахстан": "KZT", "kazakhstan": "KZT", "kz": "KZT",
    "узбекистан": "UZS", "uzbekistan": "UZS", "uz": "UZS",
    
    # Америка
    "сша": "USD", "usa": "USD", "united states": "USD", "us": "USD",
    "канада": "CAD", "canada": "CAD", "ca": "CAD",
    "мексика": "MXN", "mexico": "MXN", "mx": "MXN",
    "бразилия": "BRL", "brazil": "BRL", "br": "BRL",
    "аргентина": "ARS", "argentina": "ARS", "ar": "ARS",
    "чили": "CLP", "chile": "CLP", "cl": "CLP",
    
    # Африка
    "юар": "ZAR", "south africa": "ZAR", "za": "ZAR",
    "египет": "EGP", "egypt": "EGP", "eg": "EGP",
    
    # Океания
    "австралия": "AUD", "australia": "AUD", "au": "AUD",
    "новая зеландия": "NZD", "new zealand": "NZD", "nz": "NZD",
}


def get_currency_by_country(country_name: str) -> str:
    """
    Получение валюты по названию страны
    Возвращает код валюты или None, если страна не найдена
    """
    country_lower = country_name.lower().strip()
    return COUNTRY_CURRENCY_MAP.get(country_lower)


def format_currency_name(currency_code: str) -> str:
    """Форматирование названия валюты для отображения"""
    currency_names = {
        "RUB": "рублей (RUB)",
        "USD": "долларов (USD)",
        "EUR": "евро (EUR)",
        "GBP": "фунтов (GBP)",
        "CNY": "юаней (CNY)",
        "JPY": "иен (JPY)",
        "KRW": "вон (KRW)",
        "THB": "бат (THB)",
        "VND": "донгов (VND)",
        "IDR": "рупий (IDR)",
        "MYR": "ринггитов (MYR)",
        "SGD": "долларов (SGD)",
        "PHP": "песо (PHP)",
        "ILS": "шекелей (ILS)",
        "AED": "дирхамов (AED)",
        "SAR": "риалов (SAR)",
        "KZT": "тенге (KZT)",
        "UZS": "сумов (UZS)",
        "CAD": "долларов (CAD)",
        "MXN": "песо (MXN)",
        "BRL": "реалов (BRL)",
        "ARS": "песо (ARS)",
        "CLP": "песо (CLP)",
        "ZAR": "рандов (ZAR)",
        "EGP": "фунтов (EGP)",
        "AUD": "долларов (AUD)",
        "NZD": "долларов (NZD)",
        "CHF": "франков (CHF)",
        "SEK": "крон (SEK)",
        "NOK": "крон (NOK)",
        "DKK": "крон (DKK)",
        "CZK": "крон (CZK)",
        "HUF": "форинтов (HUF)",
        "RON": "лей (RON)",
        "TRY": "лир (TRY)",
        "UAH": "гривен (UAH)",
        "BYN": "рублей (BYN)",
        "PLN": "злотых (PLN)",
        "INR": "рупий (INR)",
    }
    return currency_names.get(currency_code, f"({currency_code})")
