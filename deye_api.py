import requests
import json
import uuid

def get_test_connection():
    url = "https://developer.deyecloud.com/openmcp/mcp"
    # Генеруємо унікальний ID для нашого бота
    session_id = str(uuid.uuid4())
    
    # КЛЮЧОВИЙ МОМЕНТ: передаємо ID у спеціальному заголовку
    headers = {
        "Content-Type": "application/json",
        "Mcp-Session-Id": session_id
    }
    
    try:
        # Крок 1: Ініціалізація (Обов'язкове "привітання")
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "TelegramBot", "version": "1.0.0"}
            }
        }
        res_init = requests.post(url, json=init_req, headers=headers).json()
        
        # Якщо сервер видав помилку вже на старті — зупиняємось і показуємо її
        if "error" in res_init:
             return f"⚠️ Помилка ініціалізації:\n<pre>{json.dumps(res_init, indent=2)}</pre>"
             
        # Крок 2: Підтвердження готовності (Notification)
        requests.post(url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=headers)
        
        # Крок 3: Запит доступних інструментів
        tools_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        res_tools = requests.post(url, json=tools_req, headers=headers).json()
        
        formatted = json.dumps(res_tools, indent=2, ensure_ascii=False)
        return f"🚀 <b>БІНГО! Доступ відкрито:</b>\n<pre>{formatted[:3500]}</pre>"
        
    except Exception as e:
        return f"❌ Системна помилка: {str(e)}"
