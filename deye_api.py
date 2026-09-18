import os
import hashlib
import requests
import json

def get_test_connection():
    app_id = os.environ.get("DEYE_APP_ID", "").strip()
    app_secret = os.environ.get("DEYE_APP_SECRET", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()

    if not app_id: 
        return "🛑 Помилка: Немає App ID у змінних Vercel."

    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()

    # Офіційний європейський сервер розробників
    url = "https://eu1-developer.deyecloud.com/v1.0/account/token"
    
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "appId": app_id,
        "appSecret": app_secret,
        "email": email,
        "password": hashed_password
    }

    debug = f"📡 <b>ВІДПРАВЛЯЮ ЗАПИТ:</b>\nURL: <code>{url}</code>\n"
    debug += f"AppID: <code>{app_id}</code>\n"
    debug += f"Email: <code>{email}</code>\n\n"

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        data = res.json()
        
        if res.status_code == 200 and data.get("success"):
            return debug + f"✅ <b>УСПІХ! ТОКЕН Є!</b>\n<code>{str(data)[:250]}</code>"
        else:
            return debug + f"⚠️ <b>Відповідь Deye:</b>\n<code>{json.dumps(data, indent=2)}</code>\n\n🛑 Якщо помилка знову 'not found', значить Deye досі не додав ваш App ID у бойову базу європейського сервера."
    except Exception as e:
        return debug + f"❌ Помилка з'єднання: {e}"
