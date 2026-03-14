import asyncio
import logging
import string
import random
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def fetch_user_data(target):
    """Универсальный поиск: по ID, юзеру или ссылке"""
    try:
        # Очистка ввода
        target = target.replace("https://t.me/", "").replace("@", "").strip()
        
        # Запрос к серверам Telegram
        chat = await bot.get_chat(target)
        
        data = {
            "id": chat.id,
            "full_name": chat.full_name,
            "username": f"@{chat.username}" if chat.username else "Отсутствует",
            "bio": chat.bio if hasattr(chat, 'bio') and chat.bio else (chat.description if chat.description else "Не указано"),
            "type": chat.type
        }
        return data
    except Exception as e:
        return None

# --- КОМАНДЫ ГЕНЕРАЦИИ (БЕЗ ИЗМЕНЕНИЙ) ---
def generate_username(length=5, include_digits=False):
    chars = string.ascii_lowercase
    if include_digits: chars += string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🛠 **Sertof Team OSINT & Gen Tool**\n\n"
        "**Поиск (Lookup):**\n"
        "└ Просто отправь боту `@username`, `ID` или `ссылку` — он выдаст всё.\n\n"
        "**Генератор:**\n"
        "├ `/gen5` / `/gen6` — Свободные юзеры\n"
        "└ `/premium` — Дорогие ники"
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def gen_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    # (Код генерации из предыдущего шага остается тут)
    await message.answer("🔄 Генерация запущена... (см. логи)")

# --- ГЛАВНАЯ ФИШКА: УНИВЕРСАЛЬНЫЙ LOOKUP ---
@dp.message()
async def universal_lookup(message: types.Message):
    if not message.text or message.text.startswith('/'): return
    
    # Игнорируем обычный флуд, если это не похоже на цель поиска
    target = message.text.strip()
    
    # Визуальный эффект поиска
    msg = await message.answer("📡 *Sertof System:* Анализирую объект...")
    
    user_info = await fetch_user_data(target)
    
    if user_info:
        res = (
            f"✅ **Объект найден в базе Sertof:**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 **ID:** `{user_info['id']}`\n"
            f"👤 **Имя:** `{user_info['full_name']}`\n"
            f"🔗 **Юзер:** {user_info['username']}\n"
            f"📝 **Инфо:** {user_info['bio']}\n"
            f"📂 **Тип:** {user_info['type']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 [Открыть профиль](tg://user?id={user_info['id']})"
        )
        await msg.edit_text(res, parse_mode="Markdown")
    else:
        await msg.edit_text("❌ **Ошибка Sertof:** Объект не найден. Проверь правильность ID или юзернейма.")

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Sertof Team Pro Lookup запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
