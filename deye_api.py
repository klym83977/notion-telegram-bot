import os
import hashlib
import requests

def get_test_connection():
    # Намагаємося витягнути змінні з Vercel
    app_id = os.environ.get("DEYE_APP_ID")
    app_secret = os.environ.get("DEYE_APP_SECRET")
    email = os.environ.get("DEYE_EMAIL")
    password = os.environ.get("DEYE_PASSWORD", "")
    
    # --- БЛОК ДІАГНОСТИКИ ---
    debug = "🔍 <b>ДІАГНОСТИКА ЗМІННИХ VERCEL:</b>\n"
    debug += f"App ID: {'✅ Є (' + app_id[:4] + '...)' if app_id else '❌ ПУСТО!'}\n"
    debug += f"App Secret: {'✅ Є' if app_secret else '❌ ПУСТО!'}\n"
    debug += f"Email: {'✅ Є (' + email + ')' if email else '❌ ПУСТО!'}\n"
    debug += f"Password: {'✅ Є' if password else '❌ ПУСТО!'}\n\n"

    # Якщо хоча б однієї головної змінної немає — далі навіть не йдемо
    if not app_id or not app_secret:
        return debug + "🛑 <b>Зупинка:</b> Бот не бачить ключів доступу! Перевірте змінні у Vercel та обов'язково зробіть Redeploy."

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
                return debug + f"✅ <b>УРА! Токен отримано!</b>\n<code>{str(data)[:200]}</code>"
            else:
                return debug + f"⚠️ <b>Сервер не дав токен:</b>\n<code>{data}</code>"
        else:
            return debug + f"❌ <b>Помилка сервера (HTTP {res.status_code}):</b>\n<code>{res.text}</code>"
            
    except Exception as e:
        return debug + f"❌ <b>Системна помилка:</b> {e}"
