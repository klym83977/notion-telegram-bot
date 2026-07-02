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

# Налаштування
nest_asyncio.apply()
app = Flask(__name__)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Ключі (беруться з Environment Variables у Vercel) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NOTION_VERSION = "2022-06-28"

user_pending_tasks: Dict[int, dict] = {}

# --- Функції Notion ---
def create_notion_task(task_text, status, priority, tag, deadline_iso=None):
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": NOTION_VERSION}
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

# --- Ініціалізація бота ---
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start_command(update, context):
    await update.message.reply_text("✅ Привіт! Пиши задачі або надсилай голосові.")

async def process_task_text(update, context, task_text):
    user_id = update.message.from_user.id
    found_dates = search_dates(task_text, languages=['uk'], settings={'PREFER_DATES_FROM': 'future'})
    deadline_iso = found_dates[0][1].strftime("%Y-%m-%d") if found_dates else None
    user_pending_tasks[user_id] = {"text": task_text, "deadline": deadline_iso}

    keyboard = [
        [InlineKeyboardButton("📥 Беклог", callback_data="status_Беклог"), InlineKeyboardButton("🔥 В процесі", callback_data="status_В процесі")],
        [InlineKeyboardButton("✅ Готово", callback_data="status_Готово")]
    ]
    await update.message.reply_text(f'Задача: "{task_text}". Оберіть статус:', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_voice(update, context):
    await update.message.reply_text("🎧 Обробка голосу...")
    file = await context.bot.get_file(update.message.voice.file_id)
    
    # Використовуємо tempfile для роботи на сервері
    with tempfile.NamedTemporaryFile(suffix='.ogg') as ogg, tempfile.NamedTemporaryFile(suffix='.wav') as wav:
        await file.download_to_drive(ogg.name)
        # УВАГА: Якщо тут помилка "ffmpeg not found", голос на Vercel працювати не буде
        AudioSegment.from_ogg(ogg.name).export(wav.name, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav.name) as source:
            text = recognizer.recognize_google(recognizer.record(source), language="uk-UA")
            await process_task_text(update, context, text)

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    task = user_pending_tasks.get(user_id)
    
    if data.startswith("status_"):
        task["status"] = data.split("_")[1]
        keyboard = [[InlineKeyboardButton("🔥 Високий", callback_data="priority_🔥 Високий"), InlineKeyboardButton("☕ Низький", callback_data="priority_☕ Низький")]]
        await query.edit_message_text("Оберіть пріоритет:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("priority_"):
        task["priority"] = data.split("_")[1]
        keyboard = [[InlineKeyboardButton("💻 Робота", callback_data="tag_💻 Робота"), InlineKeyboardButton("🛠️ DIY", callback_data="tag_🛠️ DIY")]]
        await query.edit_message_text("Оберіть тег:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("tag_"):
        task["tag"] = data.split("_")[1]
        if create_notion_task(task["text"], task["status"], task["priority"], task["tag"], task["deadline"]):
            await query.edit_message_text("✅ Задачу додано в Notion!")
        else:
            await query.edit_message_text("❌ Помилка Notion.")

# Додавання обробників
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: process_task_text(u, c, u.message.text)))
bot_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
bot_app.add_handler(CallbackQueryHandler(button_callback))

# --- Flask Маршрути ---
@app.route('/', methods=['GET'])
def index():
    return "✅ Бот успішно працює!"

@app.route('/', methods=['POST'])
def webhook():
    body = request.get_json(force=True)
    update = Update.de_json(body, bot_app.bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.process_update(update))
    return jsonify({"status": "ok"})

# Це точка входу для Vercel
application = app
