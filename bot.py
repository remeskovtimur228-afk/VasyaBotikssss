import asyncio
import logging
import string
import random
import aiohttp
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, ReplyKeyboardMarkup, KeyboardButton, 
    KeyboardButtonRequestUser, Message
)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ SERTOF ---
def init_db():
    conn = sqlite3.connect('sertof_base.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user_id, username, full_name):
    conn = sqlite3.connect('sertof_base.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, full_name, last_seen)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username.replace("@", "") if username else None, full_name))
    conn.commit()
    conn.close()

def get_user_from_db(target):
    conn = sqlite3.connect('sertof_base.db')
    cursor = conn.cursor()
    # Ищем либо по ID, либо по юзернейму
    if target.isdigit():
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (target,))
    else:
        cursor.execute('SELECT * FROM users WHERE username = ?', (target.replace("@", ""),))
    result = cursor.fetchone()
    conn.close()
    return result

# --- ГЕНЕРАЦИЯ ЮЗЕРОВ ---
async def check_nick(username):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://t.me/{username}") as resp:
            t_text = await resp.text()
            is_tg_free = "If you have Telegram, you can contact" not in t_text
        async with session.get(f"https://fragment.com/username/{username}") as resp:
            is_fr_free = resp.status == 200
    return is_tg_free, is_fr_free

# --- КЛАВИАТУРА ---
def get_main_kb():
    buttons = [
        [KeyboardButton(text="👤 Найти ID (Выбор цели)", request_user=KeyboardButtonRequestUser(request_id=1))],
        [KeyboardButton(text="📊 Статистика базы"), KeyboardButton(text="📝 История поиска")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Система Sertof Team активирована. Я запрограммирован для глубокого анализа данных Telegram.\n\n"
        "Используй кнопку ниже, чтобы узнать ID любого человека из твоих контактов или чатов, "
        "либо просто пришли мне @username.\n\n"
        "Все найденные цели автоматически заносятся в базу данных проекта.",
        reply_markup=get_main_kb()
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def handle_gen(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    length = 5 if "5" in message.text else 6
    use_digits = "premium" in message.text
    
    status = await message.answer("🛠 Идет сканирование сети на свободные адреса...")
    
    found = []
    for _ in range(15):
        nick = ''.join(random.choice(string.ascii_lowercase + (string.digits if use_digits else "")) for _ in range(length))
        tg, fr = await check_nick(nick)
        if tg or fr:
            found.append(f"📍 @{nick} (TG: {'✅' if tg else '❌'} | FR: {'✅' if fr else '❌'})")
    
    if found:
        await status.edit_text("🛰 Свободные объекты найдены:\n\n" + "\n".join(found))
    else:
        await status.edit_text("🛰 Сканирование завершено. Свободных объектов не обнаружено.")

@dp.message(F.user_shared)
async def on_user_shared(message: Message):
    """Обработка пользователя, выбранного через кнопку"""
    user_id = message.user_shared.user_id
    # Пытаемся получить больше данных через API
    try:
        chat = await bot.get_chat(user_id)
        save_user(chat.id, chat.username, chat.full_name)
        res = (
            "🎯 Цель захвачена через выбор:\n"
            "--------------------------\n"
            f"ID: {chat.id}\n"
            f"Имя: {chat.full_name}\n"
            f"Юзер: @{chat.username or 'скрыт'}\n"
            "--------------------------\n"
            "Данные сохранены в базу Sertof."
        )
    except:
        res = f"🎯 Получен ID через выбор: {user_id}\n(Полные данные будут доступны, когда цель напишет в общие чаты)"
    
    await message.answer(res)

@dp.message(F.contact)
async def on_contact(message: Message):
    contact = message.contact
    save_user(contact.user_id, None, contact.first_name)
    await message.answer(
        f"📱 Контакт проанализирован:\nID: {contact.user_id}\nИмя: {contact.first_name}\nТел: {contact.phone_number}\n\nОбъект в базе."
    )

@dp.message(F.text == "📊 Статистика базы")
async def cmd_stats(message: types.Message):
    conn = sqlite3.connect('sertof_base.db')
    count = conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    await message.answer(f"📈 Состояние системы Sertof:\nВ базе данных зафиксировано объектов: {count}")

# --- УНИВЕРСАЛЬНЫЙ ПОИСК + ЛОГИКА БД ---
@dp.message()
async def universal_handler(message: types.Message):
    if not message.text or message.text.startswith('/'): return

    target = message.text.replace("@", "").strip()
    
    # 1. Проверяем в нашей базе данных
    db_data = get_user_from_db(target)
    
    try:
        # 2. Пытаемся обновить данные через Telegram API
        chat = await bot.get_chat(target)
        save_user(chat.id, chat.username, chat.full_name)
        
        info = (
            "📡 Прямой запрос к серверам выполнен:\n"
            "--------------------------\n"
            f"ID: {chat.id}\n"
            f"Имя: {chat.full_name}\n"
            f"Юзернейм: @{chat.username or 'нет'}\n"
            f"Био: {getattr(chat, 'bio', 'скрыто')}\n"
            "--------------------------\n"
            "Объект обновлен в базе."
        )
        await message.answer(info)
    except:
        # 3. Если API не нашло, но в базе есть — выдаем из базы
        if db_data:
            await message.answer(
                f"📂 Объект найден в локальной базе Sertof:\n"
                f"ID: {db_data[0]}\n"
                f"Юзернейм: @{db_data[1]}\n"
                f"Имя: {db_data[2]}\n"
                f"Последний раз видели: {db_data[3]}"
            )
        else:
            await message.answer("❌ Объект не найден ни в сети, ни в базе данных Sertof Team.")

# --- СТАРТ ---
async def on_startup():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="gen5", description="Поиск 5-значных ников"),
        BotCommand(command="gen6", description="Поиск 6-значных ников"),
        BotCommand(command="premium", description="Дорогие ники"),
        BotCommand(command="start", description="Запуск/Обновить меню")
    ])

async def main():
    logging.basicConfig(level=logging.INFO)
    await on_startup()
    print("Sertof DB Edition запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
