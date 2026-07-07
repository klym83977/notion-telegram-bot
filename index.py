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

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
NOTION_VERSION = "2022-06-28"

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
user_pending_tasks = {}

def create_notion_task(task_text, status, priority, tag, deadline_iso=None, image_url=None):
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
        
    # Якщо є фото, додаємо його прямо в тіло сторінки Notion
    if image_url:
        data["children"] = [
            {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": image_url}
                }
            }
        ]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def generate_markup(task_data):
    markup = InlineKeyboardMarkup()

    def btn(text, val, current_val, prefix):
        if val == current_val:
            return InlineKeyboardButton(f"✅ {text}", callback_data=f"{prefix}_{val}")
        return InlineKeyboardButton(text, callback_data=f"{prefix}_{val}")

    markup.row(InlineKeyboardButton("— 📊 СТАТУС —", callback_data="ignore"))
    markup.row(btn("Беклог", "Беклог", task_data['status'], "status"), btn("В процесі", "В процесі", task_data['status'], "status"))
    markup.row(btn("Очікування", "Очікування", task_data['status'], "status"), btn("Готово", "Готово", task_data['status'], "status"))

    markup.row(InlineKeyboardButton("— 🎯 ПРІОРИТЕТ —", callback_data="ignore"))
    markup.row(btn("🔥 Високий", "🔥 Високий", task_data['priority'], "priority"), btn("⚡ Середній", "⚡ Середній", task_data['priority'], "priority"), btn("☕ Низький", "☕ Низький", task_data['priority'], "priority"))

    markup.row(InlineKeyboardButton("— 🏷️ КАТЕГОРІЯ —", callback_data="ignore"))
    markup.row(btn("🏠 Дім", "🏠 Дім", task_data['tag'], "tag"), btn("💻 Робота", "💻 Робота", task_data['tag'], "tag"))
    markup.row(btn("🚗 Авто", "🚗 Авто", task_data['tag'], "tag"), btn("🛠️ DIY", "🛠️ DIY", task_data['tag'], "tag"))

    markup.row(InlineKeyboardButton("🚀 ЗБЕРЕГТИ В NOTION", callback_data="save_task"))
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "✅ Привіт! Я твій розумний асистент.\nПиши задачі текстом, голосом або надсилай фото з підписом!")

def process_task_text(chat_id, user_id, task_text, image_url=None):
    found_dates = search_dates(task_text, languages=['uk', 'ru'], settings={'PREFER_DATES_FROM': 'future'})
    deadline_iso = None
    date_msg = ""
    if found_dates:
        date_str, date_obj = found_dates[0]
        deadline_iso = date_obj.strftime("%Y-%m-%d")
        date_msg = f"\n📅 Розпізнано дедлайн: {deadline_iso}"

    img_msg = "\n🖼️ Додано фотографію" if image_url else ""

    user_pending_tasks[user_id] = {
        "text": task_text,
        "deadline": deadline_iso,
        "status": "Беклог",        
        "priority": "⚡ Середній",  
        "tag": None,
        "image_url": image_url
    }
    bot.send_message(
        chat_id, 
        f'📝 Задача: "{task_text}"{date_msg}{img_msg}\n\n👇 Налаштуйте параметри і натисніть Зберегти:', 
        reply_markup=generate_markup(user_pending_tasks[user_id])
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_task_text(message.chat.id, message.from_user.id, message.text)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.send_message(message.chat.id, "🖼️ Обробляю фотографію...")
    try:
        task_text = message.caption if message.caption else "Фото-задача (без підпису)"
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        imgbb_url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY}
        
        # ВИПРАВЛЕННЯ: додаємо правильний формат, щоб ImgBB не відхиляв файл
        files = {"image": ("photo.jpg", downloaded_file, "image/jpeg")}
        
        res = requests.post(imgbb_url, data=payload, files=files)
        
        if res.status_code == 200:
            image_url = res.json()["data"]["url"]
            bot.delete_message(message.chat.id, msg.message_id)
            process_task_text(message.chat.id, message.from_user.id, task_text, image_url)
        else:
            bot.edit_message_text(f"❌ Помилка ImgBB: {res.text}", chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Помилка фото: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    msg = bot.send_message(message.chat.id, "🎧 Слухаю та розпізнаю голос...")
    try:
        from static_ffmpeg import run
        ffmpeg_exe, ffprobe_exe = run.get_or_fetch_platform_executables_else_raise()
        AudioSegment.converter = ffmpeg_exe
        
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
        bot.edit_message_text(f"❌ Помилка голосу: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    user_id = call.from_user.id
    data = call.data
    task_data = user_pending_tasks.get(user_id)

    if data == "ignore":
        bot.answer_callback_query(call.id)
        return

    if not task_data:
        bot.answer_callback_query(call.id, "Зачекайте, я втратив контекст задачі. Надішліть її знову.", show_alert=True)
        return

    if data == "save_task":
        if not task_data['tag']:
            bot.answer_callback_query(call.id, "⚠️ Будь ласка, оберіть Категорію перед збереженням!", show_alert=True)
            return
            
        bot.edit_message_text("⏳ Зберігаю в Notion...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        
        success, error_msg = create_notion_task(
            task_data["text"], 
            task_data["status"], 
            task_data["priority"], 
            task_data["tag"], 
            task_data["deadline"],
            task_data.get("image_url")
        )
        
        if success:
            del user_pending_tasks[user_id]
            bot.edit_message_text(f"✅ Задачу збережено!\n\n📂 Статус: {task_data['status']}\n🎯 Пріоритет: {task_data['priority']}\n🏷️ Тег: {task_data['tag']}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.edit_message_text(f"❌ Помилка Notion!\n\nДеталі: {error_msg[:250]}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    changed = False
    if data.startswith("status_"):
        new_val = data.split("_")[1]
        if task_data['status'] != new_val:
            task_data['status'] = new_val
            changed = True
    elif data.startswith("priority_"):
        new_val = data.split("_", 1)[1]
        if task_data['priority'] != new_val:
            task_data['priority'] = new_val
            changed = True
    elif data.startswith("tag_"):
        new_val = data.split("_", 1)[1]
        if task_data['tag'] != new_val:
            task_data['tag'] = new_val
            changed = True

    if changed:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=generate_markup(task_data))
    bot.answer_callback_query(call.id)

@app.route('/', methods=['GET'])
def index_route():
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
