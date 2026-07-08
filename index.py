Python
from flask import Flask, request, jsonify
import telebot

from config import YOUR_TELEGRAM_CHAT_ID
from handlers import bot
from notion import get_todays_tasks

app = Flask(__name__)
application = app

@app.route('/', methods=['GET'])
def index_route():
    return jsonify({"status": "Main Bot is running perfectly 🚀"})

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"})
    return '!', 403

@app.route('/api/morning-brief', methods=['GET'])
def morning_brief():
    if not YOUR_TELEGRAM_CHAT_ID:
        return "Chat ID not configured", 500

    success, result = get_todays_tasks()
    if not success:
        bot.send_message(YOUR_TELEGRAM_CHAT_ID, f"❌ Помилка при отриманні вранішніх задач: {result[:100]}")
        return f"Error fetching tasks: {result}", 500
    
    tasks = []
    if 'results' in result:
        for page in result['results']:
            properties = page.get('properties', {})
            name = properties.get('Name', {}).get('title', [])
            task_name = name[0]['text']['content'] if name else "Без назви"
            status = properties.get('Status', {}).get('status', {}).get('name', 'Невідомо')
            deadline = properties.get('Deadline', {}).get('date', {}).get('start', 'Без дедлайну')
            tasks.append(f"— {task_name}\n   📂 Статус: {status}\n   📅 Дедлайн: {deadline}")

    if not tasks:
        message = "☀️ Доброго ранку! Сьогодні у вас немає термінових задач у Notion. Можна випити кави!"
    else:
        task_list = "\n\n".join(tasks)
        message = f"☀️ Доброго ранку! Твій фокус на сьогодні:\n\n{task_list}\n\nБажаю продуктивного дня!"
    
    bot.send_message(YOUR_TELEGRAM_CHAT_ID, message)
    return "Briefing sent", 200

if __name__ == "__main__":
    app.run()
