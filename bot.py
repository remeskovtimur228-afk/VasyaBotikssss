import asyncio
import random
import string
import aiohttp
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ Sertof Team ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ГЕНЕРАЦИИ ---
def generate_username(length=5, include_digits=False):
    chars = string.ascii_lowercase
    if include_digits:
        chars += string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def check_username(username):
    """Проверяет юзернейм на Fragment и Telegram"""
    async with aiohttp.ClientSession() as session:
        # Проверка на Fragment
        async with session.get(f"https://fragment.com/username/{username}") as resp:
            fragment_status = "Свободен/Аукцион" if resp.status == 200 else "Занят"
        
        # Проверка в Telegram (упрощенно через t.me)
        async with session.get(f"https://t.me/{username}") as resp:
            t_me_text = await resp.text()
            tg_status = "Свободен" if "If you have Telegram, you can contact" not in t_me_text else "Занят"
            
    return tg_status, fragment_status

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⚡️ **Sertof Team Username Tools**\n\n"
        "Команды:\n"
        "1. `/gen5` — Генерация 5-значных ников (буквы)\n"
        "2. `/gen6` — Генерация 6-значных ников (буквы)\n"
        "3. `/premium` — Дорогие ники (буквы + цифры)\n"
        "4. `/lookup [username/ID]` — Инфо об аккаунте\n\n"
        "Разработано для внутреннего пользования Sertof Team."
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def handle_gen(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Доступ закрыт. Только для Sertof Team.")

    cmd = message.text.split()[0]
    length = 5 if "5" in cmd else 6
    is_premium = "premium" in cmd
    
    await message.answer(f"🔍 Начинаю генерацию и анализ {length}-значных юзеров...")

    results = []
    for _ in range(5): # Генерируем пачкой по 5 штук для скорости
        user = generate_username(length, include_digits=is_premium)
        tg_st, fr_st = await check_username(user)
        
        if tg_st == "Свободен" or "Свободен" in fr_st:
            results.append(f"💎 `@{user}`\n   ├ TG: {tg_st}\n   ├ Fragment: [Перейти](https://fragment.com/username/{user})\n   └ Ссылка: t.me/{user}")

    if results:
        await message.answer("\n\n".join(results), parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await message.answer("Все сгенерированные ники оказались заняты. Попробуй еще раз.")

@dp.message(Command("lookup"))
async def lookup(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: `/lookup @username` или `/lookup ID`")

    target = args[1].replace("@", "")
    try:
        chat = await bot.get_chat(target)
        info = (
            f"👤 **Результат поиска Sertof Team:**\n\n"
            f"🆔 ID: `{chat.id}`\n"
            f"🏷 Имя: {chat.full_name}\n"
            f"📎 Юзер: @{chat.username if chat.username else 'Нету'}\n"
            f"📝 Био: {chat.description if chat.description else 'Пусто'}"
        )
        await message.answer(info, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: Объект не найден или бот его никогда не видел.")

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Sertof Team Bot запущен. Режим: Генератор/Lookup")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
