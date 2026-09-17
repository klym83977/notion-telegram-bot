import os
import hashlib
import requests

def get_test_connection():
    app_id_str = os.environ.get("DEYE_APP_ID", "").strip()
    app_secret = os.environ.get("DEYE_APP_SECRET", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    
    debug = f"🔍 <b>АНАЛІЗ:</b> Ключ ідеальний. Шукаємо формат...\n\n"

    if not app_id_str or not app_secret:
        return debug + "🛑 <b>Помилка:</b> Ключі відсутні у Vercel."

    # Пароль у SHA-256 (нижній регістр)
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # Перетворюємо App ID на число (Integer) для перевірки бази даних
    try:
        app_id_int = int(app_id_str)
    except:
        app_id_int = app_id_str
    
    # Тестуємо головні сервери для вашого Data Center (EMEA)
    urls = [
        "https://eu1-developer.deyecloud.com/v1.0/account/token",
        "https://developer.deyecloud.com/v1.0/account/token",
        "https://eu.deyecloud.com/v1.0/account/token"
    ]
    
    for url in urls:
        domain = url.split('//')[1].split('/')[0]
        debug += f"🌐 <b>{domain}</b>\n"
        
        # Тестуємо два формати: як Число і як Текст
        for typ, app_id_val in [("Як ЧИСЛО", app_id_int), ("Як ТЕКСТ", app_id_str)]:
            payload = {
                "appId": app_id_val,
                "appSecret": app_secret,
                "email": email,
                "password": hashed_password
            }
            
            try:
                res = requests.post(url, json=payload, timeout=5)
                data = res.json()
                
                if res.status_code == 200 and data.get("success"):
                    return debug + f"✅ <b>УРА! БІНГО!</b>\nСервер: {domain}\nФормат: {typ}\n<code>{str(data)[:250]}</code>"
                else:
                    msg = data.get('msg', 'Помилка')
                    debug += f"  ├ {typ}: {msg}\n"
            except Exception as e:
                debug += f"  ├ {typ}: Немає зв'язку\n"
        debug += "\n"
            
    return debug + "🛑 Жоден формат не підійшов. Якщо ви створили App ID сьогодні чи вчора, є висока ймовірність, що сервери Deye ще не синхронізували його (це може займати до 24 годин)."
