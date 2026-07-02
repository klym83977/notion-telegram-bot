import sys
import os
import json
import asyncio
import nest_asyncio
from http.server import BaseHTTPRequestHandler

# Додаємо корінь проекту до шляхів пошуку
sys.path.append(os.getcwd())

from telegram import Update
from notion_bot import application

# Це потрібно для стабільної роботи асинхронності у Vercel
nest_asyncio.apply()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Читаємо дані, які прислав Telegram
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        # Створюємо подію Telegram
        update = Update.de_json(data, application.bot)
        
        # Запускаємо обробку
        loop = asyncio.get_event_loop()
        
        async def process():
            await application.initialize()
            await application.process_update(update)
        
        loop.run_until_complete(process())
        
        # Обов'язково відповідаємо Telegram, що все добре (код 200)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        
    def do_GET(self):
        # Відповідь для браузера (щоб ви бачили, що бот живий)
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Notion Telegram Bot is alive and ready!")
