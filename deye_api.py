import os
import requests
import json

def get_station_list():
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    app_id = "202609161815072"  # Ваш App ID з попередніх запитів
    
    if not app_secret:
        return "❌ Помилка: DEYE_CLOUD_KEY не знайдено у змінних Vercel!"
    
    # --- КРОК 1: АВТОРИЗАЦІЯ (Отримання токена) ---
    auth_url = "https://eu1-developer.deyecloud.com/v1.0/account/token"
    
    auth_payload = {
        "appId": app_id,
        "appSecret": app_secret
    }
    
    try:
        auth_res = requests.post(auth_url, json=auth_payload, timeout=10)
        auth_data = auth_res.json()
        
        # Перевіряємо, чи успішно отримали токен
        if not auth_data.get("success"):
            return f"⚠️ <b>Помилка авторизації (Крок 1):</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
            
        # Дістаємо сам токен з відповіді
        token = auth_data.get("data", {}).get("token")
        if not token:
             return f"⚠️ <b>Токен не знайдено у відповіді:</b>\n<code>{json.dumps(auth_data, indent=2)}</code>"
             
        # --- КРОК 2: ОТРИМАННЯ СТАНЦІЙ ---
        station_url = "https://eu1-developer.deyecloud.com/v1.0/station/list"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        station_payload = {
            "page": 1,
            "limit": 10
        }
        
        stat_res = requests.post(station_url, headers=headers, json=station_payload, timeout=10)
        stat_data = stat_res.json()
        
        if stat_res.status_code == 200 and stat_data.get("success"):
            return f"✅ <b>УСПІХ! СТАНЦІЇ ЗНАЙДЕНО:</b>\n<code>{json.dumps(stat_data, indent=2)[:500]}</code>"
        else:
            return f"⚠️ <b>Помилка станцій (Крок 2):</b>\n<code>{json.dumps(stat_data, indent=2)}</code>"
            
    except Exception as e:
        return f"❌ Системна помилка: {e}"

# Аліас для сумісності з вашим handlers.py
get_test_connection = get_station_list
