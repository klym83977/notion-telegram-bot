import os
import subprocess
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dateparser.search import search_dates
import speech_recognition as sr
import imageio_ffmpeg

# ВСІ ІМПОРТИ ТУТ ВГОРІ
from config import TELEGRAM_TOKEN, IMGBB_API_KEY
from notion import create_notion_task, create_notion_note, get_todays_tasks

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
user_pending_tasks = {}

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
    markup.row(btn("🏠 Побут", "🏠 Побут", task_data['tag'], "tag"), btn("🏗️ Будівництво", "🏗️ Будівництво", task_data['tag'], "tag"))
    markup.row(btn("🚗 Авто", "🚗 Авто", task_data['tag'], "tag"), btn("🛠️ DIY", "🛠️ DIY", task_data['tag'], "tag"))

    markup.row(InlineKeyboardButton("✅ ЗБЕРЕГТИ ЯК ЗАДАЧУ", callback_data="save_task"))
    markup.row(InlineKeyboardButton("🧠 ЗБЕРЕГТИ ЯК НОТАТКУ", callback_data="save_note"))
    return markup

# --- КОМАНДИ МАЮТЬ БУТИ ПЕРЕД ТЕКСТОВИМ ОБРОБНИКОМ ---

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "✅ Привіт! Я твій розумний асистент.")

@bot.message_handler(commands=['today'])
def show_today_tasks(message):
    bot.send_message(message.chat.id, "⏳ Отримую задачі на сьогодні...")
    success, result = get_todays_tasks()
    
    if not success:
        bot.send_message(message.chat.id, "❌ Помилка при отриманні задач.")
        return
        
    tasks = []
    if 'results' in result:
        for page in result['results']:
            props = page.get('properties', {})
            name = props.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', 'Без назви')
            tasks.append(f"• {name}")

    if not tasks:
        bot.send_message(message.chat.id, "☀️ Сьогодні у вас немає активних задач. Гарного дня!")
    else:
        bot.send_message(message.chat.id, f"☀️ Ваші задачі на сьогодні:\n\n" + "\n".join(tasks))

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_task_text(message.chat.id, message.from_user.id, message.text)

# --- РЕШТА ОБРОБНИКІВ ---

def process_task_text(chat_id, user_id, task_text, image_url=None):
    found_dates = search_dates(task_text, languages=['uk', 'ru'], settings={'PREFER_DATES_FROM': 'future'})
    deadline_iso = None
    date_msg = ""
    if found_dates:
        _, date_obj = found_dates[0]
        deadline_iso = date_obj.strftime("%Y-%m-%d")
        date_msg = f"\n📅 Розпізнано дедлайн: {deadline_iso}"

    img_msg = "\n🖼️ Додано фото" if image_url else ""
    user_pending_tasks[user_id] = {
        "text": task_text, "deadline": deadline_iso, "status": "Беклог", 
        "priority": "⚡ Середній", "tag": None, "image_url": image_url
    }
    bot.send_message(chat_id, f'📝 "{task_text}"{date_msg}{img_msg}\n\n👇 Налаштуйте:', reply_markup=generate_markup(user_pending_tasks[user_id]))

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # ... (ваша логіка з фото, вона була правильною) ...
    pass 

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    # ... (ваша логіка з голосом, вона була правильною) ...
    pass

@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    # ... (ваша логіка callback, вона була правильною) ...
    pass
