import sys
import os
import asyncio
import nest_asyncio
from telegram import Update
from notion_bot import application

# Додаємо поточну директорію, щоб Python бачив notion_bot.py
sys.path.append(os.getcwd())
nest_asyncio.apply()

async def handler(request):
    """
    Це основна функція, яку викликає Vercel.
    Вона отримує запит, передає його в Telegram Application і повертає відповідь.
    """
    # Отримуємо JSON-дані запиту
    body = await request.json()
    
    # Створюємо об'єкт Update
    update = Update.de_json(body, application.bot)
    
    # Обробляємо запит
    await application.initialize()
    await application.process_update(update)
    
    # Повертаємо успішну відповідь для Vercel
    return {"status": "ok"}

# Призначаємо цю функцію як application, щоб Vercel її бачив
application = handler
