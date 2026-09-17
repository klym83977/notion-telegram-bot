import os
import hashlib
import requests

def get_test_connection():
    # .strip() автоматично видаляє всі випадкові невидимі пробіли
    app_id = os.environ.get("DEYE_APP_ID", "").strip()
    app_secret = os.environ.get("DEYE_APP_SECRET", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    debug = f"🔍 <b>ДІАГНОСТИКА:</b>\nДовжина App ID: {len(app_id)} символів.\n\n"

    if not app_id or not app_secret:
        return debug + "🛑 <b>Помилка:</b> Ключі відсутні у Vercel."

    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # Повертаємо класичну структуру (сервер Deye перевіряє саме її)
    payload = {
        "appId": app_id,
        "appSecret": app_secret,
        "email": email,
        "password": hashed_password
    }
    
    # Список всіх основних дата-центрів Deye
    urls = [
        "https://eu1-developer.deyecloud.com/v1.0/account/token",
        "https://openapi.deyecloud.com/v1.0/account/token",
        "https://api.deyecloud.com/v1.0/account/token"
    ]
    
    for url in urls:
        domain = url.split('//')[1].split('/')[0]
        debug += f"🌐 Стукаю в: <code>{domain}</code>\n"
        try:
            res = requests.post(url, json=payload, timeout=5)
            data = res.json()
            
            if res.status_code == 200 and data.get("success"):
                return debug + f"✅ <b>УРА! ЗНАЙШЛИ ПРАВИЛЬНИЙ СЕРВЕР!</b>\n<code>{str(data)[:250]}</code>"
            else:
                debug += f"⚠️ Відповідь: {data.get('msg', 'Помилка')}\n\n"
        except Exception as e:
            debug += f"❌ Помилка: {e}\n\n"
            
    return debug + "🛑 Жоден сервер не прийняв App ID. Переконайтеся, що на сайті Deye ви скопіювали саме 'App ID'."
