import os
import subprocess
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dateparser.search import search_dates
import speech_recognition as sr
from config import TELEGRAM_TOKEN, IMGBB_API_KEY
from notion import create_notion_task, create_notion_note

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
user_pending_tasks = {}

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
    # Оновлені категорії: Побут та Будівництво
    markup.row(btn("🏠 Побут", "🏠 Побут", task_data['tag'], "tag"), btn("🏗️ Будівництво", "🏗️ Будівництво", task_data['tag'], "tag"))
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
from notion import get_todays_tasks # Ви вже маєте цю функцію

@bot.message_handler(commands=['today'])
def send_todays_tasks(message):
    success, result = get_todays_tasks()
    if not success:
        bot.send_message(message.chat.id, "❌ Помилка при отриманні задач.")
        return

    # ... (тут логіка формування списку, яку ми писали раніше) ...
    # Якщо задач немає — пишете: "Сьогодні задач немає, кава чекає!"    

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
    msg = bot.send_message(message.chat.id, "🎧 Розпізнаю голос (локально)...")
    try:
        import imageio_ffmpeg
        
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        ogg_path = f"/tmp/{message.voice.file_id}.ogg"
        wav_path = f"/tmp/{message.voice.file_id}.wav"
        
        with open(ogg_path, "wb") as f:
            f.write(downloaded_file)
            
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg_exe, "-y", "-i", ogg_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="uk-UA")
            
        if os.path.exists(ogg_path): os.remove(ogg_path)
        if os.path.exists(wav_path): os.remove(wav_path)
        
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
