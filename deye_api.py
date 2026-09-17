import os
import hashlib
import requests

def get_test_connection():
    app_id = os.environ.get("DEYE_APP_ID", "").strip()
    app_secret = os.environ.get("DEYE_APP_SECRET", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    debug = f"🔍 <b>ДІАГНОСТИКА:</b>\nДовжина App ID: {len(app_id)} символів.\n\n"

    if not app_id or not app_secret:
        return debug + "🛑 <b>Помилка:</b> Ключі відсутні у Vercel."

    # Пароль має бути зашифрований у SHA-256 (нижній регістр)
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # Тіло запиту БЕЗ appId (бо тепер ми точно кладемо його в URL!)
    payload = {
        "appSecret": app_secret,
        "email": email,
        "password": hashed_password
    }
    
    # Всі офіційні дата-центри Deye з ПРАВИЛЬНИМ додаванням appId в URL
    urls = [
        f"https://eu1-developer.deyecloud.com/v1.0/account/token?appId={app_id}",
        f"https://us1-developer.deyecloud.com/v1.0/account/token?appId={app_id}",
        f"https://apc1-developer.deyecloud.com/v1.0/account/token?appId={app_id}",
        f"https://india-developer.deyecloud.com/v1.0/account/token?appId={app_id}"
    ]
    
    for url in urls:
        domain = url.split('//')[1].split('/')[0]
        debug += f"🌐 Стукаю в: <code>{domain}</code>\n"
        try:
            # Відправляємо запит (requests автоматично додає Content-Type: application/json)
            res = requests.post(url, json=payload, timeout=5)
            data = res.json()
            
            if res.status_code == 200 and data.get("success"):
                return debug + f"✅ <b>УРА! ТОКЕН ОТРИМАНО З {domain.upper()}!</b>\n<code>{str(data)[:250]}</code>"
            else:
                msg = data.get('msg', 'Помилка')
                debug += f"⚠️ Відповідь: {msg}\n\n"
        except Exception as e:
            debug += f"❌ Помилка з'єднання\n\n"
            
    return debug + "🛑 Жоден сервер не прийняв App ID. Переконайтеся, що ви створили Application на developer.deyecloud.com і скопіювали ключ звідти."
