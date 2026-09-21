import os
import requests
import json
import hashlib

def get_test_connection():
    app_id = "202609161815072"
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    # Пароль має бути зашифрований у SHA-256 (нижній регістр)
    pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # КЛЮЧОВА ЗМІНА: appId передається прямо в URL
    url = f"https://eu1-developer.deyecloud.com/v1.0/account/token?appId={app_id}"
    
    # З тіла запиту appId прибрано, тут залишається лише секрет і логін
    payload = {
        "appSecret": app_secret,
        "email": email,
        "password": pass_hash
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        
        try:
            data = res.json()
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return f"🔋 <b>Відповідь від класичного Deye API:</b>\n<pre>{formatted}</pre>"
        except json.JSONDecodeError:
            return f"🔋 <b>Текст від сервера (HTTP {res.status_code}):</b>\n<pre>{res.text}</pre>"
            
    except Exception as e:
        return f"❌ Системна помилка: {str(e)}"
