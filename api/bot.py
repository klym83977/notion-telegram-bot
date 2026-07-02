import os
import json
import requests
import nest_asyncio
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

nest_asyncio.apply()

TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

bot_app = Application.builder().token(TOKEN).build()

async def start(update, context):
    await update.message.reply_text("✅ Бот успішно запущено на чистому Vercel!")

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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Це виправить помилку "Crashed" у вікні Vercel та браузері
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("✅ Бот працює і готовий приймати запити від Telegram!".encode('utf-8'))

    def do_POST(self):
        # Ця частина приймає повідомлення від Telegram
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            update = Update.de_json(body, bot_app.bot)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(bot_app.initialize())
            loop.run_until_complete(bot_app.process_update(update))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))
