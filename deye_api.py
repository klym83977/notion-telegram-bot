import os
import requests
import json
import hashlib

def get_test_connection():
    base_url = "https://developer.deyecloud.com/openmcp/mcp"
    headers_sse = {"Accept": "text/event-stream"}
    
    post_url = None
    sse_log = ""
    
    try:
        # Крок 1: Підключаємося і чекаємо, поки сервер видасть нам Session ID (талончик)
        with requests.get(base_url, headers=headers_sse, stream=True, timeout=10) as sse_res:
            for line in sse_res.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    sse_log += line_str + "\n"
                    
                    # Шукаємо рядок від сервера, де захований наш унікальний URL для запиту
                    if line_str.startswith("data:"):
                        data_content = line_str.replace("data:", "").strip()
                        if "sessionId" in data_content or data_content.startswith("http") or data_content.startswith("/"):
                            post_url = data_content
                            break # Отримали URL — відключаємося і йдемо на Крок 2
                            
            if not post_url:
                return f"❌ Сервер не видав Session ID. Лог:\n<pre>{sse_log[:1000]}</pre>"
                
            # Якщо сервер дав відносний шлях, додаємо до нього домен
            if post_url.startswith("/"):
                post_url = "https://developer.deyecloud.com" + post_url
                
    except Exception as e:
        return f"❌ Помилка першого кроку (SSE Handshake): {str(e)}"

    # Крок 2: Відправляємо наш запит на отриманий від сервера URL
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
    
    try:
        res = requests.post(post_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        try:
            data = res.json()
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return f"🚀 <b>Успіх! Отримано доступ (URL: {post_url}):</b>\n\n<pre>{formatted[:3500]}</pre>"
        except json.JSONDecodeError:
            return f"🚀 <b>Відповідь від сервера (Текст):</b>\n\n<pre>{res.text[:3500]}</pre>"
            
    except Exception as e:
        return f"❌ Помилка POST запиту: {str(e)}"
