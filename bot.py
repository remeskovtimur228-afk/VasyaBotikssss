import logging
import random
import sqlite3
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from aiogram.exceptions import TelegramForbiddenError

# --- КОНФИГ ---
TOKEN = "8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs"
ADMIN_ID = 8443511218
DB_PATH = 'vasya.db' # Для Railway без Volume. Если есть Volume, смени на /data/vasya.db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, display_name TEXT, 
                  size REAL DEFAULT 0, last_grow TEXT, last_fight TEXT, 
                  last_task TEXT, current_task TEXT, last_race TEXT, 
                  last_casino TEXT, last_roulette TEXT, last_steal TEXT, 
                  referred_by INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS command_stats (date TEXT PRIMARY KEY, count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_u(uid, name=None, uname=None):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = c.fetchone()
    if not res and name:
        disp = f"@{uname}" if uname else name
        c.execute("INSERT INTO users (user_id, username, display_name) VALUES (?, ?, ?)", (uid, name, disp))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = c.fetchone()
    conn.close()
    return list(res) if res else None

def update_u(uid, **kwargs):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    for k, v in kwargs.items():
        c.execute(f"UPDATE users SET {k} = ? WHERE user_id = ?", (v, uid))
    conn.commit(); conn.close()

# --- МАТЮКИ И ОТВЕТЫ (Пример расширяемой структуры) ---
INSULTS = ["дристун", "хуесос", "нищеброд", "мразь", "чушка", "анальник", "ошибка природы", "баклажан", "лошара"]
RANDOM_ANSWERS = [
    "Чё ты высрал?", "Твоя мамка мной гордилась бы.", "Иди поспи, ты болен.", 
    "Слышь, завали ебало.", "Ебать ты оригинальный.", "Я твой рот на кукане вертел.",
    "Кто-то пукнул или ты заговорил?", "Твой IQ как у хлебушка.", "Очко закрой.",
    "Ты чё, бессмертный?", "У тебя вместо мозга — нитка, чтоб уши не падали."
] # Сюда можно дописать хоть 5000 строк.

# --- MIDDLEWARE (АВТО-ОБНОВЛЕНИЕ СТАТЫ В АДМИНКЕ) ---
class AdminNotifyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            # Логируем в базу
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            today = str(datetime.now().date())
            c.execute("INSERT OR IGNORE INTO command_stats (date, count) VALUES (?, 0)")
            c.execute("UPDATE command_stats SET count = count + 1 WHERE date = ?", (today,))
            conn.commit(); conn.close()
            # Обновляем инфу юзера
            get_u(event.from_user.id, event.from_user.full_name, event.from_user.username)
        return await handler(event, data)

dp.message.middleware(AdminNotifyMiddleware())

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message, command: CommandObject):
    args = command.args
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    # Рефералка
    if args and args.isdigit() and int(args) != m.from_user.id and not u[12]:
        ref_id = int(args)
        inviter = get_u(ref_id)
        if inviter:
            update_u(m.from_user.id, referred_by=ref_id, size=u[3]+0.3)
            update_u(ref_id, size=inviter[3]+0.3)
            try: await bot.send_message(ref_id, f"💎 По твоей ссылке зашел лох. Тебе и ему +0.3 см!")
            except: pass

    await m.reply(f"Здарова, {random.choice(INSULTS)}! \n\nЯ Вася, твой худший кошмар. Тут мерились хуями еще до твоего рождения. \n\nЖми /help, если не совсем тупой.")

@dp.message(Command("ref"))
async def cmd_ref(m: types.Message):
    link = await create_start_link(bot, str(m.from_user.id), encode=False)
    await m.reply(f"🔗 Твоя ссылка для заманивания лохов:\n<code>{link}</code>\nЗа каждого даю 0.3 см тебе и ему.")

@dp.message(Command("cd"))
async def cmd_cd(m: types.Message):
    u = get_u(m.from_user.id)
    def check(ts, h):
        if not ts: return "Готово"
        delta = datetime.fromisoformat(ts) + timedelta(hours=h) - datetime.now()
        if delta.total_seconds() <= 0: return "Готово"
        return f"{int(delta.total_seconds()//3600)}ч {int((delta.total_seconds()%3600)//60)}м"

    text = (f"⏳ <b>ТВОИ ОТКАТЫ:</b>\n\n"
            f"🌱 Grow: {check(u[4], 20)}\n"
            f"🎰 Casino: {check(u[9], 1)}\n"
            f"🔫 Roulette: {check(u[10], 2)}\n"
            f"🏎 Race: {check(u[7], 20)}\n"
            f"🥷 Steal: {check(u[11], 4)}")
    await m.reply(text)

@dp.message(Command("grow"))
async def cmd_grow(m: types.Message):
    u = get_u(m.from_user.id)
    if u[4] and datetime.fromisoformat(u[4]) > datetime.now() - timedelta(hours=20):
        return await m.reply("Рано еще, вялый не вырос.")
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[3] + change, 2)
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    await m.reply(f"Итог: <b>{change} см</b>. Теперь: <u>{new_s} см</u>.")

@dp.message(Command("steal"))
async def cmd_steal(m: types.Message):
    u = get_u(m.from_user.id)
    if u[11] and datetime.fromisoformat(u[11]) > datetime.now() - timedelta(hours=4):
        return await m.reply("Руки еще дрожат. Жди.")
    
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? AND size != 0 ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = c.fetchone(); conn.close()
    
    if not target: return await m.reply("Некого грабить, кругом нищета.")
    
    update_u(u[0], last_steal=datetime.now().isoformat())
    if random.random() > 0.5:
        stolen = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[3]+stolen, 2))
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.reply(f"🥷 Ты спиздил <b>{stolen} см</b> у {target[1]}!")
        try: await bot.send_message(target[0], f"🚨 Проснись, обосранец! {u[2]} украл у тебя <b>{stolen} см</b>!")
        except: pass
    else:
        await m.reply("🚨 Тебя поймали за руку. Лох ебаный.")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT display_name, size FROM users WHERE size != 0 ORDER BY size DESC LIMIT 100")
    rows = c.fetchall(); conn.close()
    text = "🌍 <b>ГЛОБАЛЬНЫЙ ТОП-100:</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    await m.reply(text)

@dp.message(Command("top_group"))
async def cmd_top_group(m: types.Message):
    if m.chat.type == 'private': return await m.reply("Это только для групп, дятел.")
    # Тут логика сложнее (нужно проверять участников), упростим до "кто в базе из этого чата"
    await m.reply("Команда в разработке (нужно разрешение админа группы на список участников).")

@dp.message(Command("give", "take"))
async def cmd_admin_edit(m: types.Message, command: CommandObject):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id = int(args[0])
        amount = float(args[1])
        u = get_u(target_id)
        if not u: return await m.reply("Нет такого юзера.")
        
        new_size = u[3] + amount if command.command == "give" else u[3] - amount
        update_u(target_id, size=round(new_size, 2))
        await m.reply("✅ Батя сделал дело.")
    except: await m.reply("Пиши: /give [id] [см]")

@dp.message()
async def auto_handler(m: types.Message):
    # Повторяшка
    if m.chat.type in ['group', 'supergroup'] and m.text and random.random() < 0.03:
        await m.answer(m.text)
    
    # Ответ на теги
    if m.text and ("вася" in m.text.lower() or (m.reply_to_message and m.reply_to_message.from_user.id == bot.id)):
        await m.reply(random.choice(RANDOM_ANSWERS))

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="grow", description="Растить"),
        BotCommand(command="steal", description="Украсть"),
        BotCommand(command="top", description="ТОП-100"),
        BotCommand(command="cd", description="Кулдауны"),
        BotCommand(command="ref", description="Рефералка"),
        BotCommand(command="status", description="Стата")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
