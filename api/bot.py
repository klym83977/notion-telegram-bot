from notion_bot import application, bot
from telegram import Update

async def handler(request):
    """Ця функція приймає сигнали від Telegram (Webhook)"""
    if request.method == "POST":
        data = await request.json()
        update = Update.de_json(data, bot)
        await application.process_update(update)
        return {"status": "ok"}
    return {"status": "ok"}
