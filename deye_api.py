import os
import requests
import json
import hashlib

def get_test_connection():
    # Ваші дані з конфігурації або напряму
    app_id = "202609161815072"
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    # Базова адреса європейського сервера з офіційної документації
    baseurl = "https://eu1-developer.deyecloud.com/v1.0"
    url = f"{baseurl}/account/token?appId={app_id}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Хешування пароля в SHA-256 (згідно з документацією)
    sha256_hash = hashlib.sha256()
    sha256_hash.update(password.encode('utf-8'))
    password_with_256 = sha256_hash.hexdigest()
    
    # Повна структура запиту згідно з офіційним прикладом
    data = {
        "appSecret": app_secret,
        "email": email,
        "companyId": "0",  # Для особистого акаунта за замовчуванням
        "password": password_with_256
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        try:
            res_json = response.json()
            formatted = json.dumps(res_json, indent=2, ensure_ascii=False)
            return f"🔋 <b>Відповідь від Deye API (HTTP {response.status_code}):</b>\n<pre>{formatted}</pre>"
        except json.JSONDecodeError:
            return f"🔋 <b>Текст від сервера (HTTP {response.status_code}):</b>\n<pre>{response.text}</pre>"
            
    except Exception as err:
        return f"❌ Системна помилка: {str(err)}"
