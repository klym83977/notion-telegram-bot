import os
import requests
import json
import hashlib

def get_test_connection():
    # Нова адреса MCP сервера зі скріншота
    url = "https://developer.deyecloud.com/openmcp/mcp"
    
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    app_id = "202609161815072"
    
    pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
    # Спробуємо відправити запит до MCP у форматі JSON-RPC 2.0
    # Просимо список інструментів (щоб зрозуміти, що сервер живий і готовий спілкуватися)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {
            "appId": app_id,
            "appSecret": app_secret,
            "email": email,
            "password": pass_hash
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        
        # Форматуємо відповідь красиво, щоб побачити, що нам відповість цей новий сервер
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        return f"🚀 <b>Відповідь від нового сервера MCP:</b>\n\n<pre>{formatted_json[:3500]}</pre>"
        
    except Exception as e:
        return f"❌ Помилка з'єднання з MCP: {str(e)}"
