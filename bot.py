import asyncio
import random
import string
import aiohttp
from bs4 import BeautifulSoup
from telethon import TelegramClient
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- ТВОИ ДАННЫЕ ---
API_ID = 39018488
API_HASH = '7d916e1f8d33357651d8bec28f155c50'
BOT_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'

client = TelegramClient('scanner_session', API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_fragment(username):
    url = f"https://fragment.com/username/{username}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    status = soup.find('span', class_='tm-section-header-status')
                    return status and "Available" in status.text
                return True
    except: return True

async def is_username_free(username):
    try:
        await client.get_entity(username)
        return False
    except ValueError:
        return await check_fragment(username)
    except: return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("💎 **RING -1 Scanner (V3) Activated**\nЖми /scan")

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    status_msg = await message.answer("🔍 Сканирую...")
    found = []
    for _ in range(50):
        candidate = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(5))
        if await is_username_free(candidate):
            found.append(candidate)
            if len(found) >= 3: break
        await asyncio.sleep(0.3)

    if found:
        res = "✨ **Свободны:**\n" + "\n".join([f"• `@{f}`" for f in found])
        await status_msg.edit_text(res, parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Ничего не нашли, попробуй еще раз.")

async def main():
    await client.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
