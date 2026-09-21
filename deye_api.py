import requests
import json

def get_test_connection():
    # 1. Шукаємо правильний SSE-ендпоінт для отримання талончика
    base_urls = [
        "https://developer.deyecloud.com/openmcp/sse",
        "https://developer.deyecloud.com/openmcp/mcp/sse",
        "https://developer.deyecloud.com/openmcp/mcp"
    ]
    
    post_url = None
    sse_log = ""
    headers_sse = {"Accept": "text/event-stream"}
    
    for sse_url in base_urls:
        try:
            with requests.get(sse_url, headers=headers_sse, stream=True, timeout=5) as sse_res:
                if sse_res.status_code != 200:
                    sse_log += f"[{sse_url}] HTTP {sse_res.status_code}\n"
                    continue
                    
                is_endpoint = False
                for line in sse_res.iter_lines():
                    if line:
                        line_str = line.decode('utf-8').strip()
                        sse_log += f"{line_str}\n"
                        
                        # Шукаємо подію "endpoint", в якій сервер передає URL для запитів
                        if line_str == "event: endpoint":
                            is_endpoint = True
                        elif is_endpoint and line_str.startswith("data:"):
                            post_url = line_str.replace("data:", "").strip()
                            if post_url.startswith("/"):
                                post_url = "https://developer.deyecloud.com" + post_url
                            break
                            
            if post_url:
                break
        except Exception as e:
            sse_log += f"[{sse_url}] Помилка: {e}\n"
            
    if not post_url:
        return f"❌ Не вдалося отримати сесію (SSE). Лог:\n<pre>{sse_log[:1000]}</pre>"
        
    # 2. Сесію отримано! Виконуємо стандартне рукостискання MCP
    headers_post = {"Content-Type": "application/json"}
    
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TelegramBot", "version": "1.0"}
        }
    }
    
    try:
        # Крок 2.1: Вітаємось (Initialize)
        res_init = requests.post(post_url, json=init_req, headers=headers_post, timeout=10).json()
        if "error" in res_init:
            return f"⚠️ Помилка initialize:\n<pre>{json.dumps(res_init, indent=2)}</pre>"
            
        # Крок 2.2: Підтверджуємо, що готові (Initialized)
        requests.post(post_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=headers_post)
        
        # Крок 2.3: Просимо список інструментів
        tools_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        res_tools = requests.post(post_url, json=tools_req, headers=headers_post, timeout=10).json()
        
        return f"🚀 <b>УРА! З'ЄДНАННЯ ВСТАНОВЛЕНО!</b>\nURL сесії: {post_url}\n\n<pre>{json.dumps(res_tools, indent=2, ensure_ascii=False)[:3000]}</pre>"
        
    except Exception as e:
        return f"❌ Помилка POST запиту: {str(e)}"
