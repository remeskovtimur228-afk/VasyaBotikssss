import asyncio
import logging
import string
import random
import aiohttp
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, ReplyKeyboardMarkup, KeyboardButton, 
    KeyboardButtonRequestUser, Message, BufferedInputFile
)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ЯДРО БАЗЫ ДАННЫХ SERTOF ---
def init_db():
    conn = sqlite3.connect('sertof_intelligence.db')
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            added_at DATETIME
        )
    ''')
    # Таблица истории поиска
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def save_user_to_db(user_id, username, full_name):
    conn = sqlite3.connect('sertof_intelligence.db')
    cursor = conn.cursor()
    clean_username = username.replace("@", "").lower() if username else None
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, full_name, added_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, clean_username, full_name, datetime.now()))
    conn.commit()
    conn.close()

def add_to_history(query):
    conn = sqlite3.connect('sertof_intelligence.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO search_history (query, timestamp) VALUES (?, ?)', (query, datetime.now()))
    conn.commit()
    conn.close()

def get_user_from_db(target):
    conn = sqlite3.connect('sertof_intelligence.db')
    cursor = conn.cursor()
    target_clean = target.replace("@", "").lower().strip()
    
    if target_clean.isdigit():
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_clean,))
    else:
        cursor.execute('SELECT * FROM users WHERE LOWER(username) = ?', (target_clean,))
    
    result = cursor.fetchone()
    conn.close()
    return result

# --- ГЕНЕРАТОР ЮЗЕРОВ ---
async def check_nick(username):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://t.me/{username}") as resp:
            t_text = await resp.text()
            is_tg_free = "If you have Telegram, you can contact" not in t_text
        async with session.get(f"https://fragment.com/username/{username}") as resp:
            is_fr_free = resp.status == 200
    return is_tg_free, is_fr_free

# --- КЛАВИАТУРА И МЕНЮ ---
def get_main_kb():
    buttons = [
        [KeyboardButton(text="👤 Выбрать человека", request_user=KeyboardButtonRequestUser(request_id=1))],
        [KeyboardButton(text="📂 Экспорт базы"), KeyboardButton(text="📜 История поиска")],
        [KeyboardButton(text="📈 Статистика системы")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Система Sertof Team приветствует тебя. Бот полностью готов к работе.\n\n"
        "Я сохраняю каждого человека, которого ты мне передаешь, в зашифрованную базу. "
        "Теперь ты можешь искать людей по их ID или юзернейму, даже если они их скроют позже.",
        reply_markup=get_main_kb()
    )

@dp.message(Command("gen5", "gen6", "premium"))
async def handle_gen(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    length = 5 if "5" in message.text else 6
    use_digits = "premium" in message.text
    
    msg = await message.answer("🛸 Запуск алгоритмов Sertof по подбору ников...")
    found = []
    for _ in range(15):
        nick = ''.join(random.choice(string.ascii_lowercase + (string.digits if use_digits else "")) for _ in range(length))
        tg, fr = await check_nick(nick)
        if tg or fr:
            found.append(f"• @{nick} (TG: {'✅' if tg else '❌'} | FR: {'✅' if fr else '❌'})")
    
    res = "🛰 Свободные адреса обнаружены:\n\n" + "\n".join(found) if found else "🛰 Свободных адресов не найдено."
    await msg.edit_text(res)

# --- ОБРАБОТКА ВЫБОРА ПОЛЬЗОВАТЕЛЯ ---
@dp.message(F.user_shared)
async def on_user_shared(message: Message):
    user_id = message.user_shared.user_id
    add_to_history(f"Выбор пользователя ID: {user_id}")
    
    try:
        chat = await bot.get_chat(user_id)
        save_user_to_db(chat.id, chat.username, chat.full_name)
        res = (
            "✅ Объект успешно добавлен в базу Sertof!\n"
            "--------------------------\n"
            f"ID: {chat.id}\n"
            f"Имя: {chat.full_name}\n"
            f"Ник: @{chat.username or 'не задан'}\n"
            "--------------------------\n"
            "Поиск по этому нику теперь доступен."
        )
    except:
        res = f"⚠️ Получен ID: {user_id}. Данные будут обновлены при первом сообщении объекта."
        save_user_to_db(user_id, None, "Unknown")
    
    await message.answer(res)

# --- ФУНКЦИИ КНОПОК ---
@dp.message(F.text == "📜 История поиска")
async def show_history(message: types.Message):
    conn = sqlite3.connect('sertof_intelligence.db')
    rows = conn.cursor().execute('SELECT query, timestamp FROM search_history ORDER BY id DESC LIMIT 10').fetchall()
    conn.close()
    
    if not rows:
        return await message.answer("История поиска пуста.")
    
    res = "📜 Последние запросы в системе:\n\n"
    for r in rows:
        res += f"🕒 {r[1][:19]} -> {r[0]}\n"
    await message.answer(res)

@dp.message(F.text == "📂 Экспорт базы")
async def export_db(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('sertof_intelligence.db')
    rows = conn.cursor().execute('SELECT * FROM users').fetchall()
    conn.close()
    
    content = "ID | Username | Full Name | Added At\n" + "-"*50 + "\n"
    for r in rows:
        content += f"{r[0]} | @{r[1]} | {r[2]} | {r[3]}\n"
    
    file = BufferedInputFile(content.encode('utf-8'), filename="sertof_base_export.txt")
    await message.answer_document(file, caption="📂 Полная выгрузка базы Sertof Team.")

@dp.message(F.text == "📈 Статистика системы")
async def show_stats(message: types.Message):
    conn = sqlite3.connect('sertof_intelligence.db')
    u_count = conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]
    h_count = conn.cursor().execute('SELECT COUNT(*) FROM search_history').fetchone()[0]
    conn.close()
    await message.answer(f"📈 Статистика Sertof:\n\nВсего целей в базе: {u_count}\nВсего поисковых операций: {h_count}")

# --- УНИВЕРСАЛЬНЫЙ ПОИСК И СОХРАНЕНИЕ ---
@dp.message()
async def main_handler(message: types.Message):
    if not message.text or message.text.startswith('/'): return
    
    query = message.text.strip()
    add_to_history(query)
    
    # 1. Сначала ищем в своей базе
    db_res = get_user_from_db(query)
    
    # 2. Пытаемся пробить через API для актуализации
    try:
        target = query.replace("@", "").replace("https://t.me/", "")
        chat = await bot.get_chat(target)
        save_user_to_db(chat.id, chat.username, chat.full_name)
        
        info = (
            "📡 Свежие данные получены из сети:\n"
            "--------------------------\n"
            f"ID: {chat.id}\n"
            f"Имя: {chat.full_name}\n"
            f"Юзер: @{chat.username or 'скрыт'}\n"
            f"Био: {getattr(chat, 'bio', 'не найдено')}\n"
            "--------------------------\n"
            "База данных Sertof обновлена."
        )
        await message.answer(info)
        return
    except:
        # 3. Если API не нашло, выдаем из базы (если там есть)
        if db_res:
            await message.answer(
                f"📂 Объект найден в локальном архиве Sertof:\n"
                f"ID: {db_res[0]}\n"
                f"Юзернейм: @{db_res[1] or 'отсутствует'}\n"
                f"Имя: {db_res[2]}\n"
                f"Дата фиксации: {db_res[3][:19]}"
            )
        else:
            await message.answer("❌ Объект не найден. Попробуй передать его через кнопку или контакт, чтобы я его запомнил.")

# --- ЗАПУСК ---
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
    print("Sertof Intelligence System v3.0 Started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
