import os
import requests
import hashlib

# Якщо використовуєш файл .env, розкоментуй наступні два рядки:
# from dotenv import load_dotenv
# load_dotenv()

# 1. Підтягуємо дані зі змінних оточення
APP_ID = os.getenv("DEYE_APP_ID")
APP_SECRET = os.getenv("DEYE_APP_SECRET")
DEYE_EMAIL = os.getenv("DEYE_EMAIL")
DEYE_PASSWORD_PLAIN = os.getenv("DEYE_PASSWORD")

if not all([APP_ID, APP_SECRET, DEYE_EMAIL, DEYE_PASSWORD_PLAIN]):
    print("Помилка: Не всі змінні оточення завантажені!")
    exit(1)

# 2. Хешування пароля в SHA-256 (нижній регістр)
password_sha256 = hashlib.sha256(DEYE_PASSWORD_PLAIN.encode('utf-8')).hexdigest().lower()

# 3. Формування URL з appId в адресному рядку
url = f'https://eu1-developer.deyecloud.com/v1.0/account/token?appId={APP_ID}'

# 4. Формування заголовків та тіла
headers = {
    'Content-Type': 'application/json'
}
data = {
    "appSecret": APP_SECRET,
    "email": DEYE_EMAIL,
    "password": password_sha256
}

# 5. Відправка POST запиту
try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    response_data = response.json()
    
    if response_data.get("success"):
        access_token = response_data.get("accessToken")
        print(f"УСПІХ! Отримано Access Token:\n{access_token}")
    else:
        print(f"Помилка API: {response_data}")
        
except requests.exceptions.HTTPError as err:
    print(f"HTTP помилка: {err}")
    print(f"Детальна відповідь сервера: {response.text}")
except Exception as err:
    print(f"Помилка з'єднання: {err}")
