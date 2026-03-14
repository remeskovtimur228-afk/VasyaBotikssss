import asyncio
import logging
import string
import random
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

# --- НАСТРОЙКИ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def check_username_availability(username):
    """Проверка ника через Fragment и Telegram"""
    async with aiohttp.ClientSession() as session:
        # Проверка в ТГ через веб-интерфейс
        async with session.get(f"https://t.me/{username}") as resp:
            t_me_text = await resp.text()
            # Если страницы нет или есть кнопка связи — ник может быть свободен
            is_tg_free = "If you have Telegram, you can contact" not in t_me_text
        
        # Проверка на Fragment
        async with session.get(f"https://fragment.com/username/{username}") as resp:
            is_fragment_free = resp.status == 200 # 200 значит доступен для торга/покупки
            
    return is_tg_free, is_fragment_free

def generate_random_nick(length=5, digits=False):
    chars = string.ascii_lowercase
    if digits:
        chars += string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# --- ЛОГИКА КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я — бот Sertof Team. Меня запрограммировали для поиска данных и охоты за редкими юзернеймами.\n\n"
        "Что я умею:\n"
        "1. Пробивать инфу по ID или @юзеру (просто отправь их мне).\n"
        "2. Вытягивать данные из присланных контактов.\n"
        "3. Генерировать свободные 5-6 значные ники.\n\n"
        "Пользуйся меню команд слева. Система Sertof к твоим услугам!"
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def handle_generation(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Ошибка доступа. Скрипт настроен только на админа Sertof Team.")

    cmd = message.text
    length = 5 if "5" in cmd else 6
    use_digits = "premium" in cmd
    
    status_msg = await message.answer(f"⚙️ Система Sertof начала подбор {length}-значных ников...")
    
    found_units = []
    attempts = 0
    
    # Пытаемся найти хотя бы 3 свободных ника
    while len(found_units) < 3 and attempts < 30:
        attempts += 1
        candidate = generate_random_nick(length, use_digits)
        tg_free, fr_free = await check_username_availability(candidate)
        
        if tg_free or fr_free:
            status = "Свободен" if tg_free else "На Fragment"
            found_units.append(f"💎 @{candidate} — {status}")
            
    if found_units:
        result_text = "✅ Найдено в ходе сканирования:\n\n" + "\n".join(found_units)
        await status_msg.edit_text(result_text)
    else:
        await status_msg.edit_text("⚠️ В этом цикле свободных ников не найдено. Попробуй еще раз!")

# --- ОБРАБОТКА КОНТАКТОВ ---
@dp.message(F.contact)
async def handle_contact(message: types.Message):
    contact = message.contact
    res = (
        "🔍 Sertof Team: Данные контакта получены\n"
        "--------------------------\n"
        f"ID пользователя: {contact.user_id}\n"
        f"Имя: {contact.first_name}\n"
        f"Фамилия: {contact.last_name or 'Нет'}\n"
        f"Телефон: {contact.phone_number}\n"
        "--------------------------\n"
        "Объект зафиксирован в системе."
    )
    await message.answer(res)

# --- УНИВЕРСАЛЬНЫЙ ПОИСК (ID/Юзер) ---
@dp.message()
async def universal_lookup(message: types.Message):
    if not message.text or message.text.startswith('/'):
        return

    target = message.text.replace("@", "").replace("https://t.me/", "").strip()
    
    # Если это просто текст, пробуем пробить
    try:
        chat = await bot.get_chat(target)
        
        info = (
            "📡 Информация по запросу Sertof Team:\n"
            "--------------------------\n"
            f"ID: {chat.id}\n"
            f"Тип: {chat.type}\n"
            f"Имя/Название: {chat.full_name}\n"
            f"Юзернейм: @{chat.username if chat.username else 'отсутствует'}\n"
            f"Описание: {chat.bio if hasattr(chat, 'bio') and chat.bio else 'пусто'}\n"
            "--------------------------\n"
            "Поиск завершен успешно."
        )
        await message.answer(info)
    except Exception:
        # Если не нашли, возможно это просто мусорный текст
        pass

# --- НАСТРОЙКА МЕНЮ ПРИ ЗАПУСКЕ ---
async def on_startup():
    commands = [
        BotCommand(command="gen5", description="Найти 5-значные ники"),
        BotCommand(command="gen6", description="Найти 6-значные ники"),
        BotCommand(command="premium", description="Дорогие ники (буквы + цифры)"),
        BotCommand(command="start", description="Перезапустить систему")
    ]
    await bot.set_my_commands(commands)

async def main():
    logging.basicConfig(level=logging.INFO)
    await on_startup()
    print("Бот Sertof Team запущен. Меню настроено.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
