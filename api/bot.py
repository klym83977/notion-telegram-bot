import os
import requests
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Додаємо поточну директорію до шляхів пошуку
sys.path.append(os.getcwd())
nest_asyncio.apply()

# Це функція, яку Vercel буде бачити як "application"
async def handler(request):
    body = await request.json()
    update = Update.de_json(body, bot_application.bot)
    
    await bot_application.initialize()
    await bot_application.process_update(update)
    
    return {"status": "ok"}

# Призначаємо handler як application, щоб задовольнити Vercel
application = handler
