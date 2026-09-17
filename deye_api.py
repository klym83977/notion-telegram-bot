import os
import hashlib
import requests

def get_test_connection():
    """Функція для тестування з'єднання з Deye Cloud"""
    
    app_id = os.environ.get("DEYE_APP_ID")
    app_secret = os.environ.get("DEYE_APP_SECRET")
    email = os.environ.get("DEYE_EMAIL")
    password = os.environ.get("DEYE_PASSWORD", "")
    
    # Хешуємо пароль у SHA-256
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    url = "https://eu1-developer.deyecloud.com/v1.0/account/token"
    
    payload = {
        "appId": app_id,
        "appSecret": app_secret,
        "email": email,
        "password": hashed_password
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("success") or "access_token" in data:
                return f"✅ УРА! Токен отримано!\n\nВідповідь сервера:\n{str(data)[:200]}"
            else:
                return f"⚠️ Сервер пустив, але є помилка логіки:\n{data}"
        else:
            return f"❌ Помилка доступу (HTTP {res.status_code}):\n{res.text}"
            
    except Exception as e:
        return f"❌ Системна помилка: {e}"
