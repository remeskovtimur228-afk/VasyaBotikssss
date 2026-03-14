import asyncio
import random
import string
import aiohttp
from bs4 import BeautifulSoup
from telethon import TelegramClient
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# --- ТВОИ ДАННЫЕ ---
API_ID = 39018488
API_HASH = '7d916e1f8d33357651d8bec28f155c50'
BOT_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'

# Инициализация клиентов
# Сессия 'scanner_session' создаст файл при первом запуске
client = TelegramClient('scanner_session', API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def check_fragment(username):
    """Проверка на платформе Fragment (аукционы)."""
    url = f"https://fragment.com/username/{username}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    status = soup.find('span', class_='tm-section-header-status')
                    # Если написано Available — значит можно купить/взять
                    if status and "Available" in status.text:
                        return True
                    return False
                return True
    except:
        return True

async def is_username_free(username):
    """Двойная проверка: Telegram + Fragment."""
    try:
        # Проверка через MTProto (самая точная)
        await client.get_entity(username)
        return False # Если сущность найдена, значит занят
    except ValueError:
        # Если Telegram говорит, что не знает такого, проверяем Fragment
        return await check_fragment(username)
    except Exception:
        return False

def generate_5char():
    """Генерация случайного 5-символьного юзернейма."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(5))

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "💎 **RING -1 Scanner Activated**\n\n"
        "Я ищу свободные 5-значные юзернеймы, проверяя их через API Telegram и Fragment.\n"
        "Нажми /scan, чтобы начать поиск.",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['scan'])
async def cmd_scan(message: types.Message):
    status_msg = await message.answer("🔍 Сканирую сеть... Подождите.")
    
    found = []
    attempts = 0
    
    while len(found) < 3 and attempts < 50:
        candidate = generate_5char()
        if await is_username_free(candidate):
            found.append(candidate)
        attempts += 1
        await asyncio.sleep(0.5) # Маленькая задержка для стабильности

    if found:
        res = "✨ **Найдены свободные юзернеймы:**\n\n"
        for f in found:
            res += f"• `@{f}` — [Открыть](https://t.me/{f})\n"
        await status_msg.edit_text(res, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await status_msg.edit_text("❌ В этой итерации ничего не найдено. Попробуй еще раз через минуту.")

async def on_startup(_):
    # При первом запуске нужно будет ввести код из Telegram в консоли
    await client.start()
    print("--- СИСТЕМА RING -1 ЗАПУЩЕНА ---")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
