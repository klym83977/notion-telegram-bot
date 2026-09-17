import os
import hashlib
import requests

def get_test_connection():
    app_id = os.environ.get("DEYE_APP_ID")
    app_secret = os.environ.get("DEYE_APP_SECRET")
    email = os.environ.get("DEYE_EMAIL")
    password = os.environ.get("DEYE_PASSWORD", "")
    
    debug = "🔍 <b>ДІАГНОСТИКА:</b> Vercel бачить всі ключі ✅\n\n"

    if not app_id or not app_secret:
        return debug + "🛑 <b>Помилка:</b> Ключі не завантажились."

    # Пароль має бути зашифрований у SHA-256 і обов'язково в нижньому регістрі
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # appId передається виключно як параметр в URL
    url = f"https://eu1-developer.deyecloud.com/v1.0/account/token?appId={app_id}"
    
    # Все інше йде в тіло запиту
    payload = {
        "appSecret": app_secret,
        "email": email,
        "password": hashed_password
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        
        if res.status_code == 200 and data.get("success"):
            return debug + f"✅ <b>УРА! Токен успішно отримано!</b>\n<code>{str(data)[:250]}</code>"
        else:
            return debug + f"⚠️ <b>Відповідь сервера Deye:</b>\n<code>{data}</code>"
            
    except Exception as e:
        return debug + f"❌ <b>Системна помилка:</b> {e}"
