Python
import os
import requests
import json
import hashlib

def test_all_servers():
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    app_id = "202609161815072"
    
    if not all([app_secret, email, password]):
        return "❌ Помилка: Не всі ключі додані у Vercel!"
        
    # Хешуємо пароль (обов'язково нижній регістр)
    pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # Даємо appId і в тіло запиту (для Solarman), і в URL (для Deye)
    payload = {
        "appId": app_id, 
        "appSecret": app_secret,
        "email": email,
        "password": pass_hash
    }
    
    headers = {"Content-Type": "application/json"}
    
    # Список серверів для штурму
    servers = {
        "🇪🇺 Deye EU": f"https://eu1-developer.deyecloud.com/v1.0/account/token?appId={app_id}",
        "🌍 Deye Global": f"https://developer.deyecloud.com/v1.0/account/token?appId={app_id}",
        "☀️ Solarman": f"https://globalapi.solarmanpv.com/account/v1.0/token?appId={app_id}"
    }
    
    log = "🔍 <b>Результати штурму серверів:</b>\n\n"
    
    for name, url in servers.items():
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            data = res.json()
            
            if data.get("success"):
                token = data.get("accessToken") or data.get("access_token")
                return f"🎉 <b>БІНГО!</b>\nСервер <b>{name}</b> прийняв нас!\n\n🔑 Токен отримано:\n<code>{token[:30]}...</code>"
            else:
                msg = data.get("msg", "Невідомо")
                code = data.get("code", "-")
                log += f"❌ {name}: {msg} (Код: {code})\n"
        except Exception as e:
            log += f"⚠️ {name}: Сервер не відповів\n"
            
    log += "\n<i>Якщо всюди відмова — значить ваш ключ 100% заблокований до ручної модерації розробниками Deye. Жоден код цього не обійде.</i>"
    
    return log

# Зв'язуємо для сумісності з handlers.py
get_test_connection = test_all_servers
