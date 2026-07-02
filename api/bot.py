import os
import json
import logging
import tempfile
import requests
import asyncio
import nest_asyncio
from flask import Flask, request, jsonify
from typing import Dict

# Бібліотеки для Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Бібліотеки для дат та голосу
from dateparser.search import search_dates
import speech_recognition as sr
from pydub import AudioSegment

nest_asyncio.apply()
app = Flask(__name__)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Отримання ключів з оточення (безпечно!) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

user_pending_tasks: Dict[int, dict] = {}

def create_notion_task(task_text, status, priority, tag, deadline_iso=None):
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": status}},
            "Priority": {"select": {"name": priority}},
            "Tags": {"multi_select": [{"name": tag}]}
        }
    }
    if deadline_iso: data["properties"]["Deadline"] = {"date": {"start": deadline_iso}}
    return requests.post(url, headers=headers, json=data).status_code == 200

# --- Логіка Бот-а ---
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def process_task_text(update, context, task_text):
    user_id = update.message.from_user.id
    found_dates = search_dates(task_text, languages=['uk'], settings={'PREFER_DATES_FROM': 'future'})
    deadline_iso = found_dates[0][1].strftime("%Y-%m-%d") if found_dates else None
    user_pending_tasks[user_id] = {"text": task_text, "deadline": deadline_iso}

    keyboard = [[InlineKeyboardButton("📥 Беклог", callback_data="status_Беклог"), InlineKeyboardButton("✅ Готово", callback_data="status_Готово")]]
    await update.message.reply_text(f'Задача: "{task_text}". Оберіть статус:', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_voice(update, context):
    # УВАГА: Vercel не має ffmpeg, тому голос може не працювати без спеціального buildpack
    await update.message.reply_text("🎧 Отримав голос. Обробка може не спрацювати на Vercel (потрібен ffmpeg)...")
    # Тут логіка вашого handle_voice...

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: process_task_text(u, c, u.message.text)))
bot_app.add_handler(CallbackQueryHandler(lambda u, c: ...)) # Додайте сюди ваш button_callback

# --- Flask Webhook ---
@app.route('/', methods=['POST'])
def webhook():
    body = request.get_json(force=True)
    update = Update.de_json(body, bot_app.bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.process_update(update))
    return jsonify({"status": "ok"})

application = app
