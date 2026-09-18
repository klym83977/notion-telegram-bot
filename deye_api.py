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
    
    # Хешуємо пароль у SHA256 (вимога API)
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # --- КРОК 1: АВТОРИЗАЦІЯ ---
    auth_url = "https://globalapi.solarmanpv.com/account/v1.0/token"
    
    # Передаємо повний набір параметрів
    auth_payload = {
        "appId": app_id,
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
        
        if not auth_data.get("success"):
            return f"⚠️ <b>Помилка авторизації (Крок 1):</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
            
        token = auth_data.get("access_token")
        
        # --- КРОК 2: ОТРИМАННЯ СТАНЦІЙ ---
        station_url = "https://globalapi.solarmanpv.com/station/v1.0/list"
        
        station_headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json"
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

# Зв'язуємо функції для сумісності
get_test_connection = get_station_list
