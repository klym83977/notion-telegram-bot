import os
import requests

# Дістаємо ключ глобально для цього файлу
DEYE_KEY = os.environ.get("DEYE_CLOUD_KEY")

def get_station_list():
    """Тестовий запит для отримання списку станцій."""
    if not DEYE_KEY:
        return "❌ Помилка: DEYE_CLOUD_KEY не знайдено у змінних Vercel!"
    
    url = "https://eu1-developer.deyecloud.com/v1.0/station/list"
    
    headers = {
        "token": DEYE_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "page": 1,
        "limit": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        # Повертаємо сирий текст відповіді для тесту
        return response.text 
    except Exception as e:
        return f"❌ Помилка з'єднання: {e}"
