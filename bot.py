import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery

# ТВОЙ ТОКЕН
TOKEN = "8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs"
ADMIN_ID = 8443511218 # ID БАТИ (@sertof)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    # Ультра-резкий режим БД (WAL) для моментальной записи без блокировок
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, 
                       username TEXT, 
                       size REAL, 
                       last_grow TEXT, 
                       last_fight TEXT, 
                       last_task TEXT, 
                       current_task TEXT,
                       last_race TEXT,
                       last_casino TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS command_stats (date TEXT PRIMARY KEY, count INTEGER DEFAULT 0)''')
    
    new_cols = [
        ("last_roulette", "TEXT"),
        ("last_steal", "TEXT"),
        ("display_name", "TEXT"),
        ("referred_by", "INTEGER"),
        ("ref_count", "INTEGER DEFAULT 0")
    ]
    for col, ctype in new_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass 

    conn.commit()
    conn.close()

def log_command():
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    today = str(datetime.now().date())
    cursor.execute("INSERT OR IGNORE INTO command_stats (date, count) VALUES (?, 0)", (today,))
    cursor.execute("UPDATE command_stats SET count = count + 1 WHERE date = ?", (today,))
    conn.commit()
    conn.close()

def get_u(uid, name, uname=None):
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    display_name = f"@{uname}" if uname else name

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    
    if not res:
        # ЛОГИКА: Регистрация не с 0 см
        # Генерируем от -3 до 5 см (кроме нуля)
        start_size = round(random.uniform(-3.0, 5.0), 2)
        if abs(start_size) < 0.1: start_size = 1.0 # Защита от скучного нуля
        
        cursor.execute("INSERT INTO users (user_id, username, display_name, size, ref_count) VALUES (?, ?, ?, ?, 0)", 
                       (uid, name, display_name, start_size))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
    else:
        # Ультра-обновление имени при каждом контакте
        cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, uid))
        conn.commit()

    conn.close()
    return list(res)

def update_u(uid, **kwargs):
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    # Ультра-быстрый апдейт: коммитим сразу
    for k, v in kwargs.items():
        cursor.execute(f"UPDATE users SET {k} = ? WHERE user_id = ?", (v, uid))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def get_all_chats():
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM chats")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

# --- ГЕНЕРАТОРЫ ХУЕПЛЕТСТВА ---
INSULTS = [
    "хуеплёт", "пидорас", "уебище", "сын шлюхи", "выкидыш", "дристун", 
    "хуесос", "нищеброд", "ебло завали", "мразь", "чушка ебаная", "анальное отверстие",
    "шлепок майонезный", "ошибка презерватива", "глотатель"
]

MENTION_REPLIES = [
    "Чё те надо, псина?", "Ебало завали, я занят.", "Хули ты меня тегаешь, задрот?",
    "Твоя мамка просила передать, что ты приемный.", "Иди /grow нажимай, у тебя там минус в штанах.",
    "Слышь, воняет, отойди от экрана.", "Ты чё, бессмертный?", "Я тебя по IP вычислю и обоссу.",
    "Завали свой хлебоприемник.", "Ебать ты оригинальный (нет).", "Пошел нахуй, я сплю.",
    "Ещё раз тегнешь — отниму 10 см.", "У тебя мать святая женщина, жаль сын долбоеб.", 
    "Чё, дохуя смелый?", "Загугли 'как не быть лохом', это про тебя.", "Твой юмор хуже, чем твоя рожа.", 
    "Очко закрой, сквозит.", "Ты чё, в глаза долбишься?", "Слышь, чепуха, не отвлекай батю.", 
    "Твои сообщения — это мусор.", "Иди соси писос, салага.", "Кто пустил это животное в чат?", 
    "Твой IQ равен твоему размеру — он отрицательный.", "Скройся в тумане.", "Хули ты ноешь?", 
    "Твой батя ушел за хлебом, когда увидел твою стату.", "Чмоня детектед.", "Я твой рот на кукане вертел.", 
    "Отдохни, пупс, ты перегрелся.", "Всё, ты в моем черном списке пидорасов."
]

def get_task():
    acts = ["Высоси", "Оближи", "Засунь в очко", "Схавай", "Обоссы", "Прокукарекай", "Подожги", "Пни в ебало", "Станцуй стриптиз"]
    objs = ["дохлую крысу", "стакан мочи", "колесо трактора", "башмак соседа", "кактус", "грязную тряпку", "кусок говна"]
    locs = ["у ментовки", "перед батей", "в прямом эфире", "в одних трусах", "под гимн России", "на могиле своего достоинства"]
    return f"<b>{random.choice(acts)} {random.choice(objs)} {random.choice(locs)}!</b>"

def get_claim():
    p = ["Слышь, хуило,", "Э, ты, говно ебаное,", "Послушай сюда, уебище,", "Эй, ошибка природы,"]
    m = [
        "ты блять мылся сегодня? От тебя несет как от стада бомжей.", 
        "хули ты пялишься в экран? Иди нахуй отсюда.", 
        "у тебя ебало треснуло или ты всегда такой урод?", 
        "твою мать ебали все, кроме твоего отца.", 
        "где мои бабки, сука ебаная?", 
        "ты когда последний раз хуй свой видел за пузом, жиробас?"
    ]
    return f"{random.choice(p)} <b>{random.choice(m)}</b>"

class ChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if getattr(event, "chat", None) and event.chat.type in ['group', 'supergroup']:
            conn = sqlite3.connect('vasya_hell_final.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (event.chat.id,))
            conn.commit()
            conn.close()
        return await handler(event, data)

dp.message.middleware(ChatMiddleware())

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(m: types.Message, command: CommandObject):
    log_command()
    uid = m.from_user.id
    
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
    is_new = cursor.fetchone() is None
    conn.close()

    u = get_u(uid, m.from_user.full_name, m.from_user.username)

    if is_new:
        msg = f"Здорово, {random.choice(INSULTS)}! Твоя судьба определена: ты вошел в игру с размером <b>{u[2]} см</b>. "
        if u[2] < 0:
            msg += "Ты сразу в минусе, лох."
        else:
            msg += "Неплохой старт для выкидыша."
        
        # Рефералка при старте
        if command.args:
            try:
                ref_id = int(command.args)
                if ref_id != uid:
                    referrer = get_u(ref_id, "Unknown")
                    new_ref_cnt = (referrer[13] if len(referrer) > 13 else 0) + 1
                    update_u(ref_id, size=round(referrer[2] + 2.0, 2), ref_count=new_ref_cnt)
                    update_u(uid, referred_by=ref_id)
                    try:
                        await bot.send_message(ref_id, f"📈 <b>УЛЬТРА-ОБНОВЛЕНИЕ:</b> Твой реферал зашел. Тебе накинули <b>+2.0 см</b> моментально!")
                    except: pass
            except: pass
        await m.answer(msg)
    else:
        await m.answer(f"Чё приперся, {random.choice(INSULTS)}? Твой статус: <b>{u[2]} см</b>. Работай, сука.")

@dp.message(Command("ref"))
async def ref_cmd(m: types.Message):
    log_command()
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={m.from_user.id}"
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT ref_count FROM users WHERE user_id = ?", (m.from_user.id,))
    cnt = cursor.fetchone()[0] or 0
    conn.close()
    await m.answer(f"🤝 <b>ТВОЯ ССЫЛКА ДЛЯ РАБОВ:</b>\n<code>{ref_link}</code>\n\nПригласил: <b>{cnt}</b> лохов. За каждого +2 см.")

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    log_command()
    await m.answer(
        "<b>ИНСТРУКЦИЯ ДЛЯ ДЕБИЛОВ:</b>\n\n"
        "/zadanie — Квест\n/grow — Расти (20ч)\n/status — Дно\n/ref — Рефералка\n"
        "/fight — Пизделовка\n/casino — Казик (1ч)\n/race — Гонки (20ч)\n"
        "/roulette — Рулетка (2ч)\n/steal — Украсть см (4ч)\n/top — Лидеры\n/buy — Донат"
    )

@dp.message(Command("zadanie"))
async def zadanie(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    now = str(datetime.now().date())
    if u[5] == now:
        await m.answer(f"Твоё задание: <i>{u[6]}</i>. Вали делать!")
    else:
        t = get_task()
        update_u(m.from_user.id, last_task=now, current_task=t)
        await m.answer(f"Слушай, {random.choice(INSULTS)}. Твой квест: 🔥 {t}")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[3] and datetime.fromisoformat(u[3]) > datetime.now() - timedelta(hours=20):
        await m.answer("Твой вялый еще не готов. Жди 20 часов.")
        return
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[2] + change, 2)
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    await m.answer(f"Результат: <b>{change} см</b>. Теперь у тебя <b>{new_s} см</b>.")

@dp.message(Command("status"))
async def status(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ"
    await m.answer(f"📊 <b>ДОСЬЕ:</b>\nДлина: <b>{s} см</b>\nРанг: {r}\nСтатус: {random.choice(INSULTS)}")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if random.random() > 0.93: # Чуть поднял шанс
        win = round(random.uniform(1.0, 3.5), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.answer(f"🤜 <b>ПОБЕДА!</b> +<b>{win} см</b>. Ты сегодня не такой уж и лох.")
    else:
        loss = round(random.uniform(0.6, 2.5), 2)
        update_u(u[0], size=round(u[2]-loss, 2))
        await m.answer(f"💀 <b>ОБОССАН!</b> -<b>{loss} см</b>.")

@dp.message(Command("race"))
async def race(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[7] and datetime.fromisoformat(u[7]) > datetime.now() - timedelta(hours=20):
        return await m.answer("Машина в ремонте. Жди 20ч.")
    await m.answer("🏎 <b>Гонка началась...</b>")
    await asyncio.sleep(1.5)
    if random.random() > 0.55:
        update_u(u[0], size=round(u[2]+0.8, 2), last_race=datetime.now().isoformat())
        await m.answer("🏁 Вин! +0.8 см.")
    else:
        update_u(u[0], size=round(u[2]-1.1, 2), last_race=datetime.now().isoformat())
        await m.answer("💩 В кювете. -1.1 см.")

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[8] and datetime.fromisoformat(u[8]) > datetime.now() - timedelta(hours=1):
        return await m.answer("Казик закрыт на дезинфекцию от таких как ты.")
    if random.random() > 0.75:
        update_u(u[0], size=round(u[2]+4.0, 2), last_casino=datetime.now().isoformat())
        await m.answer("🎰 <b>ДЖЕКПОТ!</b> +4.0 см.")
    else:
        update_u(u[0], size=round(u[2]-3.0, 2), last_casino=datetime.now().isoformat())
        await m.answer("🎰 <b>ЗЕРО!</b> -3.0 см.")

@dp.message(Command("roulette"))
async def roulette(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    # Быстрая проверка времени через update_u напрямую не выйдет, берем из базы
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT last_roulette FROM users WHERE user_id = ?", (u[0],))
    last_r = cursor.fetchone()[0]
    conn.close()
    if last_r and datetime.fromisoformat(last_r) > datetime.now() - timedelta(hours=2):
        return await m.answer("Ствол еще горячий. Жди 2ч.")
    update_u(u[0], last_roulette=datetime.now().isoformat())
    if random.random() < 0.16:
        update_u(u[0], size=round(u[2]-5.0, 2))
        await m.answer("💥 <b>ВЫСТРЕЛ!</b> -5.0 см.")
    else:
        update_u(u[0], size=round(u[2]+1.2, 2))
        await m.answer("💨 Осечка. На радостях вырос на 1.2 см.")

@dp.message(Command("steal"))
async def steal(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = cursor.fetchone()
    conn.close()
    if not target: return await m.answer("Некого грабить.")
    if random.random() > 0.6:
        stolen = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[2]+stolen, 2), last_steal=datetime.now().isoformat())
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.answer(f"🥷 Подрезал у {target[1]} целых <b>{stolen} см</b>!")
    else:
        update_u(u[0], size=round(u[2]-2.0, 2), last_steal=datetime.now().isoformat())
        await m.answer(f"🚨 Тебя поймали. Оторвали 2 см.")

@dp.message(Command("top"))
async def top(m: types.Message):
    log_command()
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, size FROM users ORDER BY size DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    text = "🏆 <b>УЛЬТРА-ЛИДЕРБОРД ГИГАНТОВ:</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    await m.answer(text)

@dp.message(Command("buy"))
async def buy_stars(m: types.Message):
    await bot.send_invoice(m.chat.id, title="0.5 см чести", description="Донат Васе", 
                           payload="buy_05", provider_token="", currency="XTR",
                           prices=[LabeledPrice(label="0.5 см", amount=15)])

@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pcq.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    update_u(m.from_user.id, size=round(u[2] + 0.5, 2))
    await m.answer("🤑 Бабки на базе. +0.5 см.")

@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    users_cnt = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    await m.answer(f"👑 Батя в здании. Лохов в базе: {users_cnt}\nРассылка: /sendall [текст]")

@dp.message(Command("sendall"))
async def sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    text = m.text.replace("/sendall", "").strip()
    targets = list(set(get_all_users() + get_all_chats()))
    for t_id in targets:
        try:
            await bot.send_message(t_id, f"📢 <b>ОБЪЯВЛЕНИЕ:</b>\n{text}")
            await asyncio.sleep(0.05)
        except: pass
    await m.answer("✅ Готово.")

@dp.message()
async def auto_reply(m: types.Message):
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if m.text and "вася" in m.text.lower():
        await m.reply(random.choice(MENTION_REPLIES))
    elif m.chat.type != 'private' and random.random() < 0.04:
        await m.answer(get_claim())

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="grow", description="Растить"),
        BotCommand(command="status", description="Статус"),
        BotCommand(command="top", description="Лидерборд"),
        BotCommand(command="ref", description="Рефка"),
        BotCommand(command="fight", description="Пизделовка"),
        BotCommand(command="casino", description="Казино"),
        BotCommand(command="race", description="Гонки"),
        BotCommand(command="roulette", description="Рулетка"),
        BotCommand(command="steal", description="Украсть")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
