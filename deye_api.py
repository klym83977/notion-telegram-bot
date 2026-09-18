import os
import requests
import json
import hashlib

def get_station_list():
    # Дістаємо пошту і пароль з Vercel
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    if not email or not password:
        return "❌ Помилка: DEYE_EMAIL або DEYE_PASSWORD не знайдено у змінних Vercel!"
    
    # 1. Створюємо SHA256 хеш пароля (так вимагає додаток Deye/Solarman)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # URL для авторизації (мобільний API Solarman)
    auth_url = "https://globalapi.solarmanpv.com/account/v1.0/token"
    
    auth_payload = {
        "appSecret": "1001",  # Стандартний секрет мобільного додатку
        "email": email,
        "password": password_hash
    }
    
    # Маскуємося під додаток
    auth_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Solarman/1.0"
    }
    
    try:
        # --- КРОК 1: АВТОРИЗАЦІЯ ---
        auth_res = requests.post(auth_url, json=auth_payload, headers=auth_headers, timeout=10)
        auth_data = auth_res.json()
        
        if not auth_data.get("success"):
            return f"⚠️ <b>Помилка авторизації (Крок 1):</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
            
        token = auth_data.get("access_token")
        if not token:
             return f"⚠️ <b>Токен не знайдено у відповіді:</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
             
        # --- КРОК 2: ОТРИМАННЯ СТАНЦІЙ ---
        station_url = "https://globalapi.solarmanpv.com/station/v1.0/list"
        
        station_headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Solarman/1.0"
        }
        
        station_payload = {
            "page": 1,
            "limit": 10
        }
        
        stat_res = requests.post(station_url, headers=station_headers, json=station_payload, timeout=10)
        stat_data = stat_res.json()
        
        if stat_res.status_code == 200 and stat_data.get("success"):
            return f"✅ <b>УСПІХ! СТАНЦІЇ ЗНАЙДЕНО:</b>\n<code>{json.dumps(stat_data, indent=2)[:500]}</code>"
        else:
            return f"⚠️ <b>Помилка станцій (Крок 2):</b>\n<code>{json.dumps(stat_data, indent=2)}</code>"
            
    except Exception as e:
        return f"❌ Системна помилка: {e}"

get_test_connection = get_station_list
