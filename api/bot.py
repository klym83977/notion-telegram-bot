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

# Спроба підключити ffmpeg всередині Vercel
try:
    from static_ffmpeg import run
    ffmpeg_exe, ffprobe_exe = run.get_or_fetch_platform_executables_else_raise()
    AudioSegment.converter = ffmpeg_exe
except Exception as e:
    print(f"Попередження щодо ffmpeg: {e}")

nest_asyncio.apply()
app = Flask(__name__)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Ключі (з Environment Variables у Vercel) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NOTION_VERSION = "2022-06-28"

user_pending_tasks: Dict[int, dict] = {}

def create_notion_task(task_text, status, priority, tag, deadline_iso=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": status}},
            "Priority": {"select": {"name": priority}},
            "Tags": {"multi_select": [{"name": tag}]}
        }
    }
    if deadline_iso: 
        data["properties"]["Deadline"] = {"date": {"start": deadline_iso}}
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Помилка відправки в Notion: {e}")
        return False

# --- Логіка Бот-платформи ---
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я твій розумний асистент.\n"
        "Пиши мені задачі текстом або відправляй голосові повідомлення!"
    )

async def process_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE, task_text: str):
    user_id = update.message.from_user.id
    
    found_dates = search_dates(task_text, languages=['uk', 'ru'], settings={'PREFER_DATES_FROM': 'future'})
    deadline_iso = None
    date_msg = ""

    if found_dates:
        date_str, date_obj = found_dates[0]
        deadline_iso = date_obj.strftime("%Y-%m-%d")
        date_msg = f"\n📅 Розпізнано дедлайн: {deadline_iso}"

    user_pending_tasks[user_id] = {
        "text": task_text,
        "deadline": deadline_iso,
        "status": None,
        "priority": None,
        "tag": None
    }

    keyboard = [
        [InlineKeyboardButton("📥 Беклог", callback_data="status_Беклог"), InlineKeyboardButton("🔥 В процесі", callback_data="status_В процесі")],
        [InlineKeyboardButton("⏳ Очікування", callback_data="status_Очікування"), InlineKeyboardButton("✅ Готово", callback_data="status_Готово")]
    ]
    await update.message.reply_text(
        f'Задача: "{task_text}"{date_msg}\n\n1️⃣ Оберіть колонку (Статус):',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🎧 Слухаю та розпізнаю голос...")
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
            await voice_file.download_to_drive(ogg_file.name)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                audio = AudioSegment.from_ogg(ogg_file.name)
                audio.export(wav_file.name, format="wav")
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_file.name) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data, language="uk-UA")
        
        await msg.delete()
        await process_task_text(update, context, text)
        
    except Exception as e:
        logger.error(f"Помилка голосу: {e}")
        await msg.edit_text("❌ Не вдалося обробити голос. Спробуйте написати задачу текстом.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    task_data = user_pending_tasks.get(user_id)

    if not task_data:
        await query.edit_message_text("Зачекайте, я втратив контекст задачі. Спробуйте надіслати знову.")
        return

    if data.startswith("status_"):
        task_data["status"] = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("🔥 Високий", callback_data="priority_🔥 Високий"), InlineKeyboardButton("⚡ Середній", callback_data="priority_⚡ Середній")],
            [InlineKeyboardButton("☕ Низький", callback_data="priority_☕ Низький")]
        ]
        await query.edit_message_text("2️⃣ Оберіть пріоритет:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("priority_"):
        task_data["priority"] = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("🏠 Дім", callback_data="tag_🏠 Дім"), InlineKeyboardButton("💻 Робота", callback_data="tag_💻 Робота")],
            [InlineKeyboardButton("🚗 Авто", callback_data="tag_🚗 Авто"), InlineKeyboardButton("🛠️ DIY", callback_data="tag_🛠️ DIY")]
        ]
        await query.edit_message_text("3️⃣ Оберіть категорію (Тег):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("tag_"):
        task_data["tag"] = data.split("_")[1]
        await query.edit_message_text("⏳ Зберігаю в Notion...")

        success = create_notion_task(
            task_text=task_data["text"],
            status=task_data["status"],
            priority=task_data["priority"],
            tag=task_data["tag"],
            deadline_iso=task_data["deadline"]
        )

        if success:
            del user_pending_tasks[user_id]
            await query.edit_message_text(
                f"✅ Задачу додано!\n\n"
                f"📂 Статус: {task_data['status']}\n"
                f"🎯 Пріоритет: {task_data['priority']}\n"
                f"🏷️ Тег: {task_data['tag']}"
            )
        else:
            await query.edit_message_text("❌ Помилка Notion. Перевірте назви колонок.")

bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: process_task_text(u, c, u.message.text)))
bot_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
bot_app.add_handler(CallbackQueryHandler(button_callback))

# --- Flask Сервер ---
@app.route('/', methods=['GET'])
def index():
    return "✅ Бот на Vercel працює стабільно з усіма функціями!"

@app.route('/', methods=['POST'])
def webhook():
    body = request.get_json(force=True)
    update = Update.de_json(body, bot_app.bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.process_update(update))
    return jsonify({"status": "ok"})

application = app
