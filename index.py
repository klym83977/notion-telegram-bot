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
from datetime import date

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
YOUR_TELEGRAM_CHAT_ID = os.environ.get("YOUR_TELEGRAM_CHAT_ID") 

IMGBB_API_KEY = "a6f01e2115287b5dbd7a28cc37e957d1"
NOTION_NOTES_DATABASE_ID = "3968d5cea7038028b795fc847d23b4d8"
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
        
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

def create_notion_note(note_text, tag, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    data = {
        "parent": {"database_id": NOTION_NOTES_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": note_text}}]}
        }
    }
    
    if tag:
        data["properties"]["Tags"] = {"multi_select": [{"name": tag}]}
        
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

def generate_markup(task_data):
    markup = InlineKeyboardMarkup()

    def btn(text, val, current_val, prefix):
        if val == current_val:
            return InlineKeyboardButton(f"✅ {text}", callback_data=f"{prefix}_{val}")
        return InlineKeyboardButton(text, callback_data=f"{prefix}_{val}")

    markup.row(InlineKeyboardButton("— 📊 СТАТУС (для задач) —", callback_data="ignore"))
    markup.row(btn("Беклог", "Беклог", task_data['status'], "status"), btn("В процесі", "В процесі", task_data['status'], "status"))
    markup.row(btn("Очікування", "Очікування", task_data['status'], "status"), btn("Готово", "Готово", task_data['status'], "status"))

    markup.row(InlineKeyboardButton("— 🎯 ПРІОРИТЕТ (для задач) —", callback_data="ignore"))
    markup.row(btn("🔥 Високий", "🔥 Високий", task_data['priority'], "priority"), btn("⚡ Середній", "⚡ Середній", task_data['priority'], "priority"), btn("☕ Низький", "☕ Низький", task_data['priority'], "priority"))

    markup.row(InlineKeyboardButton("— 🏷️ КАТЕГОРІЯ —", callback_data="ignore"))
    markup.row(btn("🏠 Дім", "🏠 Дім", task_data['tag'], "tag"), btn("💻 Робота", "💻 Робота", task_data['tag'], "tag"))
    markup.row(btn("🚗 Авто", "🚗 Авто", task_data['tag'], "tag"), btn("🛠️ DIY", "🛠️ DIY", task_data['tag'], "tag"))

    markup.row(InlineKeyboardButton("✅ ЗБЕРЕГТИ ЯК ЗАДАЧУ", callback_data="save_task"))
    markup.row(InlineKeyboardButton("🧠 ЗБЕРЕГТИ ЯК НОТАТКУ", callback_data="save_note"))
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
        f'📝 Текст: "{task_text}"{date_msg}{img_msg}\n\n👇 Налаштуйте параметри і натисніть Зберегти:', 
        reply_markup=generate_markup(user_pending_tasks[user_id])
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_task_text(message.chat.id, message.from_user.id, message.text)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.send_message(message.chat.id, "🖼️ Обробляю фотографію...")
    try:
        task_text = message.caption if message.caption else "Фото-нотатка (без підпису)"
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        imgbb_url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY}
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
    msg = bot.send_message(message.chat.id, "🎧 Розпізнаю голос...")
    try:
        # ВКАЗУЄМО ШЛЯХ ДО /tmp ДЛЯ FFMPG
        os.environ["STATIC_FFMPEG_CACHE"] = "/tmp/static-ffmpeg"
        
        from static_ffmpeg import run
        ffmpeg_exe, ffprobe_exe = run.get_or_fetch_platform_executables_else_raise()
        AudioSegment.converter = ffmpeg_exe
        
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Використовуємо /tmp для збереження файлів
        with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.ogg', delete=False) as ogg_file:
            ogg_file.write(downloaded_file)
            ogg_file.flush()
            with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.wav', delete=False) as wav_file:
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
        bot.answer_callback_query(call.id, "Контекст втрачено. Надішліть повідомлення знову.", show_alert=True)
        return

    if data == "save_task":
        if not task_data['tag']:
            bot.answer_callback_query(call.id, "⚠️ Оберіть Категорію!", show_alert=True)
            return
            
        bot.edit_message_text("⏳ Зберігаю задачу...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        success, error_msg = create_notion_task(task_data["text"], task_data["status"], task_data["priority"], task_data["tag"], task_data["deadline"], task_data.get("image_url"))
        
        if success:
            del user_pending_tasks[user_id]
            bot.edit_message_text(f"✅ Задачу збережено!\n📂 Статус: {task_data['status']}\n🎯 Пріоритет: {task_data['priority']}\n🏷️ Тег: {task_data['tag']}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.edit_message_text(f"❌ Помилка: {error_msg[:250]}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if data == "save_note":
        bot.edit_message_text("⏳ Зберігаю нотатку...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        success, error_msg = create_notion_note(task_data["text"], task_data["tag"], task_data.get("image_url"))
        
        if success:
            del user_pending_tasks[user_id]
            tag_msg = f"\n🏷️ Тег: {task_data['tag']}" if task_data['tag'] else "\n🏷️ Без тегу"
            bot.edit_message_text(f"🧠 Нотатку успішно збережено у базу знань!{tag_msg}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.edit_message_text(f"❌ Помилка Notion: {error_msg[:250]}", chat_id=call.message.chat.id, message_id=call.message.message_id)
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

def get_todays_tasks():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    today_iso = date.today().strftime("%Y-%m-%d")
    
    query_data = {
        "filter": {
            "and": [
                {"property": "Status", "status": {"does_not_equal": "Готово"}},
                {"or": [
                    {"property": "Deadline", "date": {"equals": today_iso}},
                    {"property": "Status", "status": {"equals": "В процесі"}}
                ]}
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=query_data)
        return response.status_code == 200, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return False, str(e)

@app.route('/', methods=['GET'])
def index_route():
    return "✅ Бот працює!"

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

application = app
