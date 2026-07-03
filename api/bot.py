import os
import tempfile
import logging
import requests
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from dateparser.search import search_dates
import speech_recognition as sr
from pydub import AudioSegment

# Підключення ffmpeg на Vercel
try:
    from static_ffmpeg import run
    ffmpeg_exe, ffprobe_exe = run.get_or_fetch_platform_executables_else_raise()
    AudioSegment.converter = ffmpeg_exe
except Exception as e:
    print(f"Попередження щодо ffmpeg: {e}")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Ключі ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NOTION_VERSION = "2022-06-28"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_pending_tasks = {}

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
    except Exception:
        return False

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id, 
        "✅ Привіт! Я твій розумний асистент.\nПиши мені задачі текстом або відправляй голосові повідомлення!"
    )

def process_task_text(chat_id, user_id, task_text):
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

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📥 Беклог", callback_data="status_Беклог"), InlineKeyboardButton("🔥 В процесі", callback_data="status_В процесі"))
    markup.row(InlineKeyboardButton("⏳ Очікування", callback_data="status_Очікування"), InlineKeyboardButton("✅ Готово", callback_data="status_Готово"))

    bot.send_message(chat_id, f'Задача: "{task_text}"{date_msg}\n\n1️⃣ Оберіть колонку (Статус):', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_task_text(message.chat.id, message.from_user.id, message.text)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    msg = bot.send_message(message.chat.id, "🎧 Слухаю та розпізнаю голос...")
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
            ogg_file.write(downloaded_file)
            ogg_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                audio = AudioSegment.from_ogg(ogg_file.name)
                audio.export(wav_file.name, format="wav")
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_file.name) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data, language="uk-UA")
        
        bot.delete_message(message.chat.id, msg.message_id)
        process_task_text(message.chat.id, message.from_user.id, text)
    except Exception as e:
        bot.edit_message_text("❌ Не вдалося обробити голос. Спробуйте написати задачу текстом.", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    user_id = call.from_user.id
    data = call.data
    task_data = user_pending_tasks.get(user_id)

    if not task_data:
        bot.edit_message_text("Зачекайте, я втратив контекст задачі. Спробуйте надіслати знову.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if data.startswith("status_"):
        task_data["status"] = data.split("_")[1]
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔥 Високий", callback_data="priority_🔥 Високий"), InlineKeyboardButton("⚡ Середній", callback_data="priority_⚡ Середній"))
        markup.row(InlineKeyboardButton("☕ Низький", callback_data="priority_☕ Низький"))
        bot.edit_message_text("2️⃣ Оберіть пріоритет:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data.startswith("priority_"):
        task_data["priority"] = data.split("_")[1]
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🏠 Дім", callback_data="tag_🏠 Дім"), InlineKeyboardButton("💻 Робота", callback_data="tag_💻 Робота"))
        markup.row(InlineKeyboardButton("🚗 Авто", callback_data="tag_🚗 Авто"), InlineKeyboardButton("🛠️ DIY", callback_data="tag_🛠️ DIY"))
        bot.edit_message_text("3️⃣ Оберіть категорію (Тег):", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data.startswith("tag_"):
        task_data["tag"] = data.split("_")[1]
        bot.edit_message_text("⏳ Зберігаю в Notion...", chat_id=call.message.chat.id, message_id=call.message.message_id)

        success = create_notion_task(
            task_text=task_data["text"],
            status=task_data["status"],
            priority=task_data["priority"],
            tag=task_data["tag"],
            deadline_iso=task_data["deadline"]
        )

        if success:
            del user_pending_tasks[user_id]
            bot.edit_message_text(
                f"✅ Задачу додано!\n\n📂 Статус: {task_data['status']}\n🎯 Пріоритет: {task_data['priority']}\n🏷️ Тег: {task_data['tag']}",
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
        else:
            bot.edit_message_text("❌ Помилка Notion. Перевірте назви колонок у вашій базі даних.", chat_id=call.message.chat.id, message_id=call.message.message_id)

@app.route('/', methods=['GET'])
def index():
    return "✅ Бот на Vercel працює ідеально з Telebot!"

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"})
    return '!', 403

application = app
