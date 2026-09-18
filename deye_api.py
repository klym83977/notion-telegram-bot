import os
import requests
import json

def get_station_list():
    deye_key = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    
    if not deye_key:
        return "❌ Помилка: DEYE_CLOUD_KEY не знайдено у змінних Vercel!"
    
    # Офіційний європейський сервер розробників
    url = "https://eu1-developer.deyecloud.com/v1.0/station/list"
    
    headers = {
        "Authorization": f"Bearer {deye_key}",
        "token": deye_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "page": 1,
        "limit": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            return f"✅ <b>УСПІХ! СТАНЦІЇ ЗНАЙДЕНО:</b>\n<code>{json.dumps(data, indent=2)[:300]}</code>"
        else:
            return f"⚠️ <b>Відповідь сервера:</b>\n<code>{json.dumps(data, indent=2)}</code>"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {e}"

# Явно оголошуємо обидві функції, щобhandlers.py не видавав помилку імпорту
def get_test_connection():
    return get_station_list()
