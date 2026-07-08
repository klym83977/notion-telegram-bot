import os
import logging

logging.basicConfig(level=logging.INFO)

# --- ЗМІННІ З VERCEL ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
YOUR_TELEGRAM_CHAT_ID = os.environ.get("YOUR_TELEGRAM_CHAT_ID") 

IMGBB_API_KEY = "a6f01e2115287b5dbd7a28cc37e957d1"
NOTION_NOTES_DATABASE_ID = "3968d5cea7038028b795fc847d23b4d8"
NOTION_VERSION = "2022-06-28"

if not TELEGRAM_TOKEN:
    logging.error("ПОМИЛКА: Не встановлено TELEGRAM_TOKEN у Vercel!")
