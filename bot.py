import asyncio
import logging
import string
import random
import aiohttp
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, ReplyKeyboardMarkup, KeyboardButton, 
    KeyboardButtonRequestUser, Message
)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685 # Твой ID для доступа к генератору

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ SERTOF ---
def init_db():
    conn = sqlite3.connect('sertof_data.db')
    cursor = conn.cursor()
    # Таблица пользователей (ID, ник, имя)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            saved_at DATETIME
        )
    ''')
    # Таблица истории (кто что искал)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            time DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(uid, uname, fname):
    conn = sqlite3.connect('sertof_data.db')
    cursor = conn.cursor()
    # Сохраняем ник без @ и в нижнем регистре для точного поиска
    clean_uname = uname.replace("@", "").lower() if uname else None
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, full_name, saved_at)
        VALUES (?, ?, ?, ?)
    ''', (uid, clean_uname, fname, datetime.now()))
    conn.commit()
    conn.close()

def log_search(uid, query):
    conn = sqlite3.connect('sertof_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (user_id, query, time) VALUES (?, ?, ?)', 
                   (uid, query, datetime.now()))
    conn.commit()
    conn.close()

def search_in_db(target):
    conn = sqlite3.connect('sertof_data.db')
    cursor = conn.cursor()
    target_clean = target.replace("@", "").lower().strip()
    
    if target_clean.isdigit():
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_clean,))
    else:
        cursor.execute('SELECT * FROM users WHERE username = ?', (target_clean,))
    
    res = cursor.fetchone()
    conn.close()
    return res

# --- ГЕНЕРАТОР НИКОВ ---
async def check_availability(nick):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://t.me/{nick}") as r1:
            t_free = "If you have Telegram, you can contact" not in await r1.text()
        async with session.get(f"https://fragment.com/username/{nick}") as r2:
            f_free = r2.status == 200
    return t_free, f_free

# --- КЛАВИАТУРА ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Узнать ID (Выбор)", request_user=KeyboardButtonRequestUser(request_id=1))],
        [KeyboardButton(text="📜 Моя история")],
        [KeyboardButton(text="📊 Статус системы")]
    ], resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать в систему Sertof Team.\n\n"
        "Я помогу тебе узнать ID любого пользователя и найти информацию о нем. "
        "Просто отправь мне @юзернейм или используй кнопку выбора.\n\n"
        "Все найденные пользователи сохраняются в общую базу поиска.",
        reply_markup=main_menu()
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def gen_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Эта функция доступна только разработчикам Sertof.")
    
    length = 5 if "5" in message.text else 6
    chars = string.ascii_lowercase + (string.digits if "premium" in message.text else "")
    
    status = await message.answer("🛰 Поиск свободных юзеров в сети...")
    found = []
    for _ in range(12):
        nick = "".join(random.choice(chars) for _ in range(length))
        t, f = await check_availability(nick)
        if t or f:
            found.append(f"🔹 @{nick} (TG: {'✅' if t else '❌'} | FR: {'✅' if f else '❌'})")
            
    await status.edit_text("✅ Результаты генерации:\n\n" + "\n".join(found) if found else "❌ Ничего не найдено.")

@dp.message(F.user_shared)
async def shared_user(message: Message):
    uid = message.user_shared.user_id
    log_search(message.from_user.id, f"Выбор ID {uid}")
    
    try:
        chat = await bot.get_chat(uid)
        save_to_db(chat.id, chat.username, chat.full_name)
        await message.answer(
            f"🎯 Объект зафиксирован:\nID: {chat.id}\nИмя: {chat.full_name}\nЮзер: @{chat.username or 'скрыт'}"
        )
    except:
        save_to_db(uid, None, "Unknown")
        await message.answer(f"🎯 ID получен: {uid}\nПолные данные будут в базе после обновления.")

@dp.message(F.contact)
async def contact_user(message: Message):
    c = message.contact
    save_to_db(c.user_id, None, c.first_name)
    log_search(message.from_user.id, f"Контакт {c.user_id}")
    await message.answer(f"📱 Контакт сохранен:\nID: {c.user_id}\nИмя: {c.first_name}\nТел: {c.phone_number}")

@dp.message(F.text == "📜 Моя история")
async def my_history(message: Message):
    conn = sqlite3.connect('sertof_data.db')
    rows = conn.cursor().execute('SELECT query, time FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 5', 
                                 (message.from_user.id,)).fetchall()
    conn.close()
    if not rows: return await message.answer("Твоя история поиска пуста.")
    res = "📜 Твои последние запросы:\n" + "\n".join([f"• {r[1][:16]} -> {r[0]}" for r in rows])
    await message.answer(res)

@dp.message(F.text == "📊 Статус системы")
async def stats(message: Message):
    conn = sqlite3.connect('sertof_data.db')
    cnt = conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    await message.answer(f"📈 База Sertof Team содержит объектов: {cnt}")

@dp.message()
async def global_search(message: Message):
    if not message.text or message.text.startswith("/"): return
    query = message.text.strip()
    log_search(message.from_user.id, query)
    
    db_res = search_in_db(query)
    
    try:
        target = query.replace("@", "").replace("https://t.me/", "")
        chat = await bot.get_chat(target)
        save_to_db(chat.id, chat.username, chat.full_name)
        await message.answer(
            f"📡 Данные из сети:\nID: {chat.id}\nИмя: {chat.full_name}\nЮзер: @{chat.username or 'нет'}\nБио: {getattr(chat, 'bio', 'скрыто')}"
        )
    except:
        if db_res:
            await message.answer(
                f"📂 Найдено в архиве Sertof:\nID: {db_res[0]}\nЮзер: @{db_res[1] or 'отсутствует'}\nИмя: {db_res[2]}\nДата записи: {db_res[3][:16]}"
            )
        else:
            await message.answer("❌ Объект не найден. Попробуй передать его кнопкой.")

# --- ЗАПУСК ---
async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="gen5", description="Ники 5 симв."),
        BotCommand(command="gen6", description="Ники 6 симв."),
        BotCommand(command="premium", description="Премиум ники"),
        BotCommand(command="start", description="Запуск системы")
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
