import os
import requests
import json
import hashlib

def get_station_list():
    # Збираємо всі необхідні змінні з Vercel
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    # Ваш App ID
    app_id = "202609161815072"
    
    if not all([app_secret, email, password]):
        return "❌ Помилка: Переконайтеся, що DEYE_CLOUD_KEY, DEYE_EMAIL та DEYE_PASSWORD додані у Vercel!"
    
    # Хешуємо пароль у SHA256 і обов'язково переводимо в нижній регістр (вимога Deye)
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # --- КРОК 1: АВТОРИЗАЦІЯ ---
    # УВАГА: Deye вимагає передавати appId саме в URL посилання!
    auth_url = f"https://eu1-developer.deyecloud.com/v1.0/account/token?appId={app_id}"
    
    auth_payload = {
        "appSecret": app_secret,
        "email": email,
        "password": password_hash
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        auth_res = requests.post(auth_url, json=auth_payload, headers=headers, timeout=10)
        auth_data = auth_res.json()
        
        # Перевірка помилки
        if not auth_data.get("success"):
            return f"⚠️ <b>Помилка авторизації (Крок 1):</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
            
        # У Deye ключ називається accessToken (з великої літери T)
        token = auth_data.get("accessToken")
        
        if not token:
             return f"⚠️ <b>Токен не знайдено у відповіді:</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
             
        # --- КРОК 2: ОТРИМАННЯ СТАНЦІЙ ---
        station_url = "https://eu1-developer.deyecloud.com/v1.0/station/list"
        
        station_headers = {
            "Authorization": f"bearer {token}",  # Deye вимагає 'bearer' з маленької літери
            "Content-Type": "application/json"
        }
        
        station_payload = {
            "page": 1,
            "limit": 10
        }
        
        stat_res = requests.post(station_url, headers=station_headers, json=station_payload, timeout=10)
        stat_data = stat_res.json()
        
        if stat_res.status_code == 200 and stat_data.get("success"):
            return f"✅ <b>УСПІХ! СТАНЦІЇ ЗНАЙДЕНО:</b>\n<code>{json.dumps(stat_data, indent=2)[:700]}</code>"
        else:
            return f"⚠️ <b>Помилка станцій (Крок 2):</b>\n<code>{json.dumps(stat_data, indent=2)}</code>"
            
    except Exception as e:
        return f"❌ Системна помилка: {e}"

# Зв'язуємо функції для сумісності
get_test_connection = get_station_list
