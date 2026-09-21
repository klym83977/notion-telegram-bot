import os
import requests
import json
import hashlib
import uuid

def get_test_connection():
    # Генеруємо унікальний ідентифікатор сесії для кожного запиту
    session_id = uuid.uuid4().hex
    # Додаємо sessionId як параметр до URL
    url = f"https://developer.deyecloud.com/openmcp/mcp?sessionId={session_id}"
    
    app_secret = os.environ.get("DEYE_CLOUD_KEY", "").strip()
    email = os.environ.get("DEYE_EMAIL", "").strip()
    password = os.environ.get("DEYE_PASSWORD", "").strip()
    app_id = "202609161815072"
    
    pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest().lower()
    
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
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        
        try:
            data = res.json()
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            return f"🚀 <b>Відповідь від сервера MCP (JSON):</b>\n\n<pre>{formatted_json[:3500]}</pre>"
        except json.JSONDecodeError:
            return f"🚀 <b>Відповідь від сервера MCP (Текст):</b>\n\n<pre>{res.text[:3500]}</pre>"
            
    except Exception as e:
        return f"❌ Помилка з'єднання з MCP: {str(e)}"
