import os
import time
import hashlib
import requests

def get_test_connection():
    app_id = os.environ.get("DEYE_APP_ID")
    app_secret = os.environ.get("DEYE_APP_SECRET")
    email = os.environ.get("DEYE_EMAIL")
    password = os.environ.get("DEYE_PASSWORD", "")
    
    debug = "🔍 <b>ДІАГНОСТИКА:</b> Vercel бачить всі ключі ✅\n\n"

    if not app_id or not app_secret:
        return debug + "🛑 <b>Помилка:</b> Ключі все ще не завантажились."

    # Хешуємо пароль (Deye зазвичай вимагає SHA256 для безпеки)
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # 1. Формуємо обов'язкові параметри безпеки
    timestamp = str(int(time.time() * 1000)) # Поточний час у мілісекундах
    
    # 2. Робимо цифровий підпис: SHA256(appId + appSecret + timestamp)
    sign_string = app_id + app_secret + timestamp
    sign = hashlib.sha256(sign_string.encode('utf-8')).hexdigest()
    
    # 3. Кладемо appId, timestamp та sign у ЗАГОЛОВКИ (Headers), де їх чекає сервер
    headers = {
        "Content-Type": "application/json",
        "appId": app_id,
        "timestamp": timestamp,
        "sign": sign
    }
    
    # В самому тілі запиту залишаємо лише логін та пароль
    payload = {
        "email": email,
        "password": hashed_password
    }
    
    url = "https://eu1-developer.deyecloud.com/v1.0/account/token"
    
    try:
        # Відправляємо запит з заголовками (headers=headers)
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        
        if res.status_code == 200 and data.get("success"):
            return debug + f"✅ <b>УРА! Токен успішно отримано!</b>\n<code>{str(data)[:250]}</code>"
        else:
            return debug + f"⚠️ <b>Відповідь сервера Deye:</b>\n<code>{data}</code>"
            
    except Exception as e:
        return debug + f"❌ <b>Системна помилка:</b> {e}"
