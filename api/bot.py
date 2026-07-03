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

# --- Генерація єдиного вікна з кнопками ---
def generate_markup(task_data):
    markup = InlineKeyboardMarkup()

    # СТАТУС
    s_b = "✅ 📥 Беклог" if task_data['status'] == "Беклог" else "📥 Беклог"
    s_p = "✅ 🔥 В процесі" if task_data['status'] == "В процесі" else "🔥 В процесі"
    s_w = "✅ ⏳ Очікування" if task_data['status'] == "Очікування" else "⏳ Очікування"
    s_d = "✅ ✅ Готово" if task_data['status'] == "Готово" else "✅ Готово"

    markup.row(InlineKeyboardButton(s_b, callback_data="status_Беклог"),
               InlineKeyboardButton(s_p, callback_data="status_В процесі"))
    markup.row(InlineKeyboardButton(s_w, callback_data="status_Очікування"),
               InlineKeyboardButton(s_d, callback_data="status_Готово"))

    # ПРІОРИТЕТ
    p_h = "✅ 🔥 Вис" if task_data['priority'] == "🔥 Високий" else "🔥 Високий"
    p_m = "✅ ⚡ Сер" if task_data['priority'] == "⚡ Середній" else "⚡ Середній"
    p_l = "✅ ☕ Низ" if task_data['priority'] == "☕ Низький" else "☕ Низький"

    markup.row(InlineKeyboardButton(p_h, callback_data="priority_🔥 Високий"),
               InlineKeyboardButton(p_m, callback_data="priority_⚡ Середній"),
               InlineKeyboardButton(p_l, callback_data="priority_☕ Низький"))

    # КАТЕГОРІЯ (ТЕГ)
    t_h = "✅ 🏠 Дім" if task_data['tag'] == "🏠 Дім" else "🏠 Дім"
    t_w = "✅ 💻 Робота" if task_data['tag'] == "💻 Робота" else "💻 Робота"
    t_a = "✅ 🚗 Авто" if task_data['tag'] == "🚗 Авто" else "🚗 Авто"
    t_d = "✅ 🛠️ DIY" if task_data['tag'] == "🛠️ DIY" else "🛠️ DIY"

    markup.row(InlineKeyboardButton(t_h, callback_data="tag_🏠 Дім"),
               InlineKeyboardButton(t_w, callback_data="tag_💻 Робота"))
    markup.row(InlineKeyboardButton(t_a, callback_data="tag_🚗 Авто"),
               InlineKeyboardButton(t_d, callback_data="tag_🛠️ DIY"))

    # КНОПКА ЗБЕРЕЖЕННЯ
    markup.row(InlineKeyboardButton("🚀 ЗБЕРЕГТИ В NOTION", callback_data="save_task"))

    return markup

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

    # Зберігаємо задачу з вибраними параметрами за замовчуванням
    user_pending_tasks[user_id] = {
        "text": task_text,
        "deadline": deadline_iso,
        "status": "Беклог",        # За замовчуванням
        "priority": "⚡ Середній",  # За замовчуванням
        "tag": None               # Користувач має обрати сам
    }

    bot.send_message(
        chat_id, 
        f'📝 Задача: "{task_text}"{date_msg}\n\n👇 Налаштуйте параметри і натисніть Зберегти:', 
        reply_markup=generate_markup(user_pending_tasks[user_id])
    )

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
        bot.answer_callback_query(call.id, "Зачекайте, я втратив контекст задачі. Надішліть її знову.", show_alert=True)
        return

    # Якщо натиснута кнопка "ЗБЕРЕГТИ"
    if data == "save_task":
        if not task_data['tag']:
            bot.answer_callback_query(call.id, "⚠️ Будь ласка, оберіть Категорію (Тег) перед збереженням!", show_alert=True)
            return

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
                f"✅ Задачу збережено!\n\n📂 Статус: {task_data['status']}\n🎯 Пріоритет: {task_data['priority']}\n🏷️ Тег: {task_data['tag']}",
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
        else:
            bot.edit_message_text("❌ Помилка Notion. Перевірте назви колонок.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    # Якщо користувач просто перемикає значення
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

    # Оновлюємо клавіатуру лише якщо було змінено статус
    if changed:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=generate_markup(task_data)
        )
    
    bot.answer_callback_query(call.id)

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
