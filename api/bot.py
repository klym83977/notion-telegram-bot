import os
import requests
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Flask(__name__)

# --- Конфігурація ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

bot_app = Application.builder().token(TOKEN).build()

# --- Логіка бота ---
async def start(update, context):
    await update.message.reply_text("✅ Бот успішно запущено на Vercel з Flask!")

async def handle_text(update, context):
    task_text = update.message.text
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": "Беклог"}}
        }
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        await update.message.reply_text("✅ Задачу додано в Notion!")
    else:
        await update.message.reply_text(f"❌ Помилка Notion: {res.text}")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# --- Flask Маршрути (WSGI, який вимагає Vercel) ---
@app.route('/', methods=['GET'])
def index():
    return "✅ Бот працює на Flask і готовий приймати запити від Telegram!"

@app.route('/', methods=['POST'])
def webhook():
    try:
        body = request.get_json(force=True)
        update = Update.de_json(body, bot_app.bot)

        # Виконуємо асинхронний код бота
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.process_update(update))
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Змінна application, як WSGI-додаток для Vercel
application = app
