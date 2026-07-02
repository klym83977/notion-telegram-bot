import os
import requests
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

nest_asyncio.apply()

TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

bot_app = Application.builder().token(TOKEN).build()

async def start(update, context):
    await update.message.reply_text("✅ Бот успішно запущено на чистому Vercel!")

async def handle_text(update, context):
    task_text = update.message.text
    url = "[https://api.notion.com/v1/pages](https://api.notion.com/v1/pages)"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": "Беклог"}}
        }
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        await update.message.reply_text("✅ Задачу додано в Notion!")
    else:
        await update.message.reply_text(f"❌ Помилка Notion: {res.text}")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def handler(request):
    try:
        body = await request.json()
        update = Update.de_json(body, bot_app.bot)
        await bot_app.initialize()
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

application = handler
