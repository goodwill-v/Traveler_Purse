import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()
API_KEY = os.getenv("CURRENCY_API_KEY")



def get_current_rate(default: str = "USD", currencies: list[str] = ["EUR", "GBP", "JPY"]) :
    url = "https://api.exchangerate.host/live"
    params = {
        "access_key": API_KEY,
        "source": default,
        "currencies": ",".join(currencies)
        # ",".join(currencies) означает объединение в строку с разделителем-запятой
    }

    response = requests.get(url, params=params)
    data = response.json()
    return data

if __name__ == "__main__":
    data = get_current_rate(default="RUB", currencies=["USD", "EUR", "GBP", "JPY", "CNY"])

    print(data)
  
    
    