import requests

def get_test_connection():
    url = "https://developer.deyecloud.com/openmcp/mcp"
    
    try:
        # Робимо той самий GET-запит, який видав 400, але цього разу уважно слухаємо відповідь
        headers = {
            "Accept": "text/event-stream"
        }
        
        res = requests.get(url, headers=headers, timeout=10)
        
        # Виводимо статус і повний текст, який сервер нам повернув
        log = f"Статус код: HTTP {res.status_code}\n\nТіло відповіді:\n{res.text}"
        
        return f"🔍 <b>Що приховує сервер (HTTP 400):</b>\n<pre>{log[:3500]}</pre>"
        
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
