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
ADMIN_ID = 8318867685 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ SERTOF (ОПТИМИЗИРОВАНА ПОД НАГРУЗКУ) ---
def init_db():
    # Используем check_same_thread=False для работы в асинхронной среде
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            saved_at DATETIME
        )
    ''')
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
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    cursor = conn.cursor()
    clean_uname = uname.replace("@", "").lower() if uname else None
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, full_name, saved_at)
            VALUES (?, ?, ?, ?)
        ''', (uid, clean_uname, fname, datetime.now()))
        conn.commit()
    finally:
        conn.close()

def log_search(uid, query):
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO history (user_id, query, time) VALUES (?, ?, ?)', 
                       (uid, query, datetime.now()))
        conn.commit()
    finally:
        conn.close()

def search_in_db(target):
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    cursor = conn.cursor()
    target_clean = target.replace("@", "").lower().strip()
    try:
        if target_clean.isdigit():
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_clean,))
        else:
            cursor.execute('SELECT * FROM users WHERE username = ?', (target_clean,))
        return cursor.fetchone()
    finally:
        conn.close()

# --- ГЕНЕРАТОР НИКОВ ---
async def check_availability(nick):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://t.me/{nick}", timeout=5) as r1:
                t_free = "If you have Telegram, you can contact" not in await r1.text()
            async with session.get(f"https://fragment.com/username/{nick}", timeout=5) as r2:
                f_free = r2.status == 200
            return t_free, f_free
        except:
            return False, False

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
        "Система Sertof Team активирована и работает в штатном режиме.\n\n"
        "Отправь @юзернейм или воспользуйся кнопкой для фиксации ID. "
        "База обновляется мгновенно.",
        reply_markup=main_menu()
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def gen_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Доступ к ядру генерации только для Sertof Admin.")
    
    length = 5 if "5" in message.text else 6
    chars = string.ascii_lowercase + (string.digits if "premium" in message.text else "")
    
    status = await message.answer("🛰 Поиск свободных адресов...")
    found = []
    for _ in range(12):
        nick = "".join(random.choice(chars) for _ in range(length))
        t, f = await check_availability(nick)
        if t or f:
            found.append(f"🔹 @{nick} (TG: {'✅' if t else '❌'} | FR: {'✅' if f else '❌'})")
            
    await status.edit_text("✅ Результаты анализа:\n\n" + "\n".join(found) if found else "❌ Свободных ников не найдено.")

@dp.message(F.user_shared)
async def shared_user(message: Message):
    uid = message.user_shared.user_id
    log_search(message.from_user.id, f"ID Selection {uid}")
    
    try:
        chat = await bot.get_chat(uid)
        save_to_db(chat.id, chat.username, chat.full_name)
        await message.answer(
            f"🎯 Объект зафиксирован в системе:\nID: {chat.id}\nИмя: {chat.full_name}\nЮзер: @{chat.username or 'не указан'}"
        )
    except Exception as e:
        save_to_db(uid, None, "Unknown")
        await message.answer(f"🎯 ID получен: {uid}\n(Данные будут дополнены при обнаружении объекта в сети)")

@dp.message(F.contact)
async def contact_user(message: Message):
    c = message.contact
    save_to_db(c.user_id, None, c.first_name)
    log_search(message.from_user.id, f"Contact Shared {c.user_id}")
    await message.answer(f"📱 Контакт добавлен в базу:\nID: {c.user_id}\nИмя: {c.first_name}\nТел: {c.phone_number}")

@dp.message(F.text == "📜 Моя история")
async def my_history(message: Message):
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    try:
        rows = conn.cursor().execute('SELECT query, time FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 5', 
                                     (message.from_user.id,)).fetchall()
        if not rows: return await message.answer("Твоя история пуста.")
        res = "📜 Твои последние запросы:\n" + "\n".join([f"• {r[1][:16]} -> {r[0]}" for r in rows])
        await message.answer(res)
    finally:
        conn.close()

@dp.message(F.text == "📊 Статус системы")
async def stats(message: Message):
    conn = sqlite3.connect('sertof_data.db', check_same_thread=False)
    try:
        cnt = conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]
        await message.answer(f"📈 Глобальная база Sertof содержит: {cnt} объектов.")
    finally:
        conn.close()

@dp.message()
async def global_search(message: Message):
    if not message.text or message.text.startswith("/"): return
    query = message.text.strip()
    log_search(message.from_user.id, query)
    
    # Сначала пытаемся обновить данные через сеть
    try:
        target = query.replace("@", "").replace("https://t.me/", "")
        chat = await bot.get_chat(target)
        save_to_db(chat.id, chat.username, chat.full_name)
        await message.answer(
            f"📡 Актуальные данные объекта:\nID: {chat.id}\nИмя: {chat.full_name}\nЮзер: @{chat.username or 'отсутствует'}\nБио: {getattr(chat, 'bio', 'скрыто')}"
        )
    except:
        # Если в сети нет (или бот не видит), ищем в нашей базе
        db_res = search_in_db(query)
        if db_res:
            await message.answer(
                f"📂 Найдено в архиве Sertof:\nID: {db_res[0]}\nЮзер: @{db_res[1] or 'отсутствует'}\nИмя: {db_res[2]}\nЗафиксирован: {db_res[3][:16]}"
            )
        else:
            await message.answer("❌ Объект не обнаружен. Попробуй передать его через контакт или кнопку выбора.")

# --- ЗАПУСК ---
async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="gen5", description="Юзеры 5 знаков"),
        BotCommand(command="gen6", description="Юзеры 6 знаков"),
        BotCommand(command="premium", description="Премиум поиск"),
        BotCommand(command="start", description="Перезагрузка системы")
    ])
    print("Sertof Stable Core запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
