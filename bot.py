import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery
from aiogram.utils.deep_linking import create_start_link

# ТВОЙ ТОКЕН И ID
TOKEN = "8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs"
ADMIN_ID = 8443511218 # ID БАТИ (@sertof)

# БАЗА ДАННЫХ
DB_NAME = 'vasya_hell_final.db' 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- БАЗА ДАННЫХ (ФИКС БАГОВ) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, 
                       username TEXT, 
                       size REAL DEFAULT 0, 
                       last_grow TEXT, 
                       last_fight TEXT, 
                       last_task TEXT, 
                       current_task TEXT,
                       last_race TEXT,
                       last_casino TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS command_stats (date TEXT PRIMARY KEY, count INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_members (chat_id INTEGER, user_id INTEGER, UNIQUE(chat_id, user_id))''')
    
    new_cols = [
        ("last_roulette", "TEXT"),
        ("last_steal", "TEXT"),
        ("display_name", "TEXT"),
        ("referred_by", "INTEGER")
    ]
    for col, ctype in new_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass 

    conn.commit()
    conn.close()

def log_command():
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        today = str(datetime.now().date())
        cursor.execute("INSERT OR IGNORE INTO command_stats (date, count) VALUES (?, 0)", (today,))
        cursor.execute("UPDATE command_stats SET count = count + 1 WHERE date = ?", (today,))
        conn.commit()
    finally:
        conn.close()

def get_u(uid, name=None, uname=None):
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        display_name = f"@{uname}" if uname else (name if name else "Чушпан")
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
        if not res:
            cursor.execute("INSERT INTO users (user_id, username, display_name, size) VALUES (?, ?, ?, 0)", (uid, name, display_name))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
            res = cursor.fetchone()
        else:
            # Обновляем имя только если оно пришло новое, чтобы не долбить базу зря
            if name or uname:
                cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, uid))
                conn.commit()
        return list(res)
    finally:
        conn.close()

def update_u(uid, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        for k, v in kwargs.items():
            cursor.execute(f"UPDATE users SET {k} = ? WHERE user_id = ?", (v, uid))
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def get_all_chats():
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM chats")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

# --- ТВОИ ОРИГИНАЛЬНЫЕ МАССИВЫ ---
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

RANDOM_ANSWERS = [
    "Да мне похуй абсолютно.", "Ты сам-то понял че высрал?", "Иди поплачь.",
    "Ага, держи в курсе, долбоеб.", "Твое мнение очень важно для нас (нет).",
    "Скажи это моему хую.", "Запятые расставь, чурка.", "Чел, ты кринж.",
    "Ты под спайсом или по жизни такой?", "Ответ убил (тебя об стену)."
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

# --- MIDDLEWARE (УБРАЛ ДУБЛИРОВАНИЕ) ---
class ChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        conn = sqlite3.connect(DB_NAME)
        try:
            cursor = conn.cursor()
            # Регистрируем только чат и участников. Юзера создаст get_u в командах.
            if getattr(event, "chat", None) and event.chat.type in ['group', 'supergroup']:
                cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (event.chat.id,))
                if getattr(event, "from_user", None):
                    cursor.execute("INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)", (event.chat.id, event.from_user.id))
            conn.commit()
        finally:
            conn.close()
        return await handler(event, data)

dp.message.middleware(ChatMiddleware())

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def start(m: types.Message, command: CommandObject):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    args = command.args
    if args and args.isdigit() and int(args) != m.from_user.id and not u[12]: 
        ref_id = int(args)
        inviter = get_u(ref_id)
        if inviter:
            update_u(m.from_user.id, referred_by=ref_id, size=round(u[2] + 0.3, 2))
            update_u(ref_id, size=round(inviter[2] + 0.3, 2))
            try:
                await bot.send_message(ref_id, f"💎 Твоя шлюшка {m.from_user.full_name} перешла по ссылке! Тебе и ему <b>+0.3 см</b>!")
            except: pass

    await m.reply(
        f"Здорово, {random.choice(INSULTS)}! Я Вася. \n\n"
        f"⚠️ <b>ВАЖНО:</b> Всё, что я тут несу — это <b>ЮМОР</b>. Я не хочу тебя обидеть, я просто так шучу, еблан. \n\n"
        f"Меня состряпал @sertof. Будем мериться хуями или ты сразу нахуй пойдешь?"
    )

@dp.message(Command("ref"))
async def cmd_ref(m: types.Message):
    log_command()
    link = await create_start_link(bot, str(m.from_user.id), encode=False)
    await m.reply(f"🔗 <b>Твоя реферальная ссылка:</b>\n<code>{link}</code>\n\nКидай её лохам. Как только кто-то запустит бота — вы оба получите по <b>+0.3 см</b>.")

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    log_command()
    await m.reply(
        "<b>ЧИТАЙ, ПОКА Я ТЕБЕ ЕБАЛО НЕ ВСКРЫЛ:</b>\n\n"
        "<u>/zadanie</u> — Ебанутый квест (раз в день)\n"
        "<u>/grow</u> — Попытка вырасти (20ч кулдаун)\n"
        "<u>/cd</u> — Посмотреть свои тайминги (кулдауны)\n"
        "<u>/status</u> — Твоя дырявая статистика\n"
        "<u>/fight</u> — Пизделовка\n"
        "<u>/casino</u> — Слить в минус (раз в 1 час)\n"
        "<u>/race</u> — Уличные гонки (20ч кулдаун)\n"
        "<u>/roulette</u> — Русская рулетка (2ч кулдаун)\n"
        "<u>/steal</u> — Спиздить у лоха (4ч кулдаун)\n"
        "<u>/buy</u> — Купить см за Звезды (донат)\n"
        "<u>/top</u> — Глобальный Топ тех, кто ебет тебя в жопу\n"
        "<u>/top_group</u> — Топ лохов этой группы\n"
        "<u>/oldes</u> — Самые старые чушпаны бота\n"
        "<u>/ref</u> — Заработать на друзьях\n"
        "<u>/info</u> — Чё это за свалка\n\n"
        f"🙏 <i>Это рофл. Не принимай близко к сердцу, {random.choice(INSULTS)}.</i>"
    )

@dp.message(Command("cd"))
async def cmd_cd(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    def check(ts, h):
        if not ts: return "✅ Готов"
        delta = datetime.fromisoformat(ts) + timedelta(hours=h) - datetime.now()
        if delta.total_seconds() <= 0: return "✅ Готов"
        s = int(delta.total_seconds())
        return f"⏳ {s//3600}ч {(s%3600)//60}м {s%60}с"

    text = (f"⏱ <b>ТВОИ ОТКАТЫ, ТОРМОЗ:</b>\n\n"
            f"🌱 Grow: {check(u[3], 20)}\n"
            f"🎰 Casino: {check(u[8], 1)}\n"
            f"🔫 Roulette: {check(u[9], 2)}\n"
            f"🏎 Race: {check(u[7], 20)}\n"
            f"🥷 Steal: {check(u[10], 4)}")
    await m.reply(text)

@dp.message(Command("info"))
async def info_cmd(m: types.Message):
    log_command()
    await m.reply("ℹ️ <b>ИНФА ДЛЯ ТУПЫХ И ОБИДЧИВЫХ:</b>\n\nСоздатель этого дурдома: @sertof. Жаловаться маме.")

@dp.message(Command("zadanie"))
async def zadanie(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    now = str(datetime.now().date())
    if u[5] == now:
        await m.reply(f"Хули ты ноешь, {random.choice(INSULTS)}? Твоё ебаное задание: <i>{u[6]}</i>. Иди делай, сука!")
    else:
        t = get_task()
        update_u(m.from_user.id, last_task=now, current_task=t)
        await m.reply(f"Слушай сюда, {random.choice(INSULTS)}. Твой квест:\n\n🔥 {t}")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[3] and datetime.fromisoformat(u[3]) > datetime.now() - timedelta(hours=20):
        return await m.reply(f"Куда лезешь, {random.choice(INSULTS)}?! Жди 20 часов.")
    
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[2] + change, 2) 
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    
    if change > 0: 
        await m.reply(f"Опа, {random.choice(INSULTS)}. Подрос на <b>{change} см</b>. Теперь: <u>{new_s} см</u>.")
    else: 
        await m.reply(f"ХА-ХА-ХА! Ушел внутрь на <b>{abs(change)} см</b>. Теперь: <u>{new_s} см</u>.")

@dp.message(Command("status"))
async def status(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм хуй" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ ПИДОРАС"
    disp = m.from_user.username if m.from_user.username else m.from_user.full_name
    await m.reply(f"📊 <b>ТВОЁ ДОСЬЕ ГОВНОЕДА ({disp}):</b>\n\nДлина: <i>{s} см</i>\nРанг: <u>{r}</u>")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if random.random() > 0.95:
        win = round(random.uniform(1.0, 3.5), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.reply(f"🤜 <b>ПОБЕДА!</b> Лови <b>+{win} см</b>. Но ты всё равно {random.choice(INSULTS)}.")
    else:
        loss = round(random.uniform(0.6, 2.5), 2)
        update_u(u[0], size=round(u[2]-loss, 2)) 
        await m.reply(f"💀 <b>ФИАСКО!</b> Минус <b>{loss} см</b>.")

@dp.message(Command("race"))
async def race(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[7] and datetime.fromisoformat(u[7]) > datetime.now() - timedelta(hours=20):
        return await m.reply(f"Жди 20 часов, {random.choice(INSULTS)}.")

    await m.reply("🏎 <b>Заезд пошел...</b>")
    await asyncio.sleep(2)
    now_ts = datetime.now().isoformat()
    if random.random() > 0.6:
        update_u(u[0], size=round(u[2]+0.7, 2), last_race=now_ts)
        await bot.send_message(m.chat.id, f"🏁 Первое место! +0.7 см.", reply_to_message_id=m.message_id)
    else:
        update_u(u[0], size=round(u[2]-1.0, 2), last_race=now_ts)
        await bot.send_message(m.chat.id, f"💩 Ты врезался в фуру. -1.0 см.", reply_to_message_id=m.message_id)

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[8] and datetime.fromisoformat(u[8]) > datetime.now() - timedelta(hours=1):
        return await m.reply(f"Казик закрыт. Приходи через час.")

    now_ts = datetime.now().isoformat()
    if random.random() > 0.8:
        update_u(u[0], size=round(u[2]+3.5, 2), last_casino=now_ts)
        await m.reply(f"🎰 <b>СУКА, ПОВЕЗЛО!</b> +3.5 см.")
    else:
        update_u(u[0], size=round(u[2]-2.5, 2), last_casino=now_ts)
        await m.reply(f"🎰 <b>ЗЕРО, ЕБЛАН!</b> -2.5 см.")

@dp.message(Command("roulette"))
async def roulette(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[9] and datetime.fromisoformat(u[9]) > datetime.now() - timedelta(hours=2):
        return await m.reply(f"Ствол перегрелся. Жди 2 часа.")

    await m.reply("🔫 <b>Крутишь барабан...</b>")
    await asyncio.sleep(1.5)
    now_ts = datetime.now().isoformat()
    update_u(u[0], last_roulette=now_ts)
    
    if random.random() < 0.16:
        loss = round(random.uniform(2.0, 5.0), 2)
        update_u(u[0], size=round(u[2]-loss, 2))
        await bot.send_message(m.chat.id, f"💥 <b>ВЫСТРЕЛ!</b> Минус <b>{loss} см</b>.", reply_to_message_id=m.message_id)
    else:
        win = round(random.uniform(0.3, 1.0), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await bot.send_message(m.chat.id, f"💨 <b>Щелчок...</b> Пронесло. +<b>{win} см</b>.", reply_to_message_id=m.message_id)

@dp.message(Command("steal"))
async def steal(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[10] and datetime.fromisoformat(u[10]) > datetime.now() - timedelta(hours=4):
        return await m.reply(f"Жди 4 часа.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? AND size != 0 ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = cursor.fetchone()
    conn.close()

    if not target: return await m.reply("Некого грабить.")

    now_ts = datetime.now().isoformat()
    update_u(u[0], last_steal=now_ts)

    if random.random() > 0.6: 
        stolen = round(random.uniform(0.2, 1.2), 2)
        update_u(u[0], size=round(u[2]+stolen, 2))
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.reply(f"🥷 Подрезал у {target[1]} целых <b>{stolen} см</b>!")
    else:
        fail = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[2]-fail, 2))
        await m.reply(f"🚨 <b>ПОПАЛСЯ!</b> Минус <b>{fail} см</b>.")

@dp.message(Command("top"))
async def top(m: types.Message):
    log_command()
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT display_name, size FROM users WHERE size != 0 ORDER BY size DESC LIMIT 100")
    rows = cursor.fetchall(); conn.close()
    text = "🌍 <b>ГЛОБАЛЬНЫЙ ТОП-100:</b>\n\n"
    for i, r in enumerate(rows, 1): text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    await m.reply(text[:4096])

@dp.message(Command("top_group"))
async def top_group(m: types.Message):
    log_command()
    if m.chat.type == 'private': return
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT u.display_name, u.size FROM users u JOIN chat_members c ON u.user_id = c.user_id WHERE c.chat_id = ? AND u.size != 0 ORDER BY u.size DESC LIMIT 50", (m.chat.id,))
    rows = cursor.fetchall(); conn.close()
    text = f"🏠 <b>ТОП ЭТОГО ЧАТА:</b>\n\n"
    for i, r in enumerate(rows, 1): text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    await m.reply(text)

@dp.message(Command("oldes"))
async def oldes(m: types.Message):
    log_command()
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT display_name FROM users ORDER BY rowid ASC LIMIT 15")
    rows = cursor.fetchall(); conn.close()
    text = "🦴 <b>ОЛДЫ БОТА:</b>\n\n"
    for i, r in enumerate(rows, 1): text += f"{i}. {r[0]}\n"
    await m.reply(text)

@dp.message(Command("buy"))
async def buy_stars(m: types.Message):
    log_command()
    await bot.send_invoice(m.chat.id, "Удлинить", "0.5 см за 15 Stars", "buy_05", "", "XTR", [LabeledPrice(label="0.5 см", amount=15)])

@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pcq.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(m: types.Message):
    u = get_u(m.from_user.id)
    update_u(m.from_user.id, size=round(u[2] + 0.5, 2))
    await m.reply(f"🤑 +0.5 см начислено!")

# --- АДМИНКА ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    chats_count = cursor.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    conn.close()
    await m.reply(f"👑 Батя, в базе {users_count} юзеров и {chats_count} чатов.")

@dp.message(Command("sendall"))
async def admin_sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    text = m.text.replace("/sendall", "").strip()
    if not text: return
    targets = list(set(get_all_users() + get_all_chats()))
    for tid in targets:
        try: 
            await bot.send_message(tid, f"📢 <b>ОТ БАТИ:</b>\n\n{text}")
            await asyncio.sleep(0.05)
        except: pass
    await m.reply("✅ Рассылка завершена.")

# --- АВТООТВЕТЫ (ФИКС КОНФЛИКТОВ) ---
@dp.message()
async def auto_handler(m: types.Message):
    # Если это команда — выходим, пусть работают Command-хендлеры
    if m.text and m.text.startswith('/'):
        return

    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    text = m.text.lower() if m.text else ""
    
    if m.chat.type != 'private' and text and random.random() < 0.01:
        return await m.answer(m.text)

    is_mentioned = "вася" in text or (m.reply_to_message and m.reply_to_message.from_user.id == bot.id)
    if is_mentioned:
        return await m.reply(random.choice(MENTION_REPLIES if random.random() > 0.5 else RANDOM_ANSWERS))
    
    if m.chat.type != 'private' and random.random() < 0.05: 
        await m.reply(get_claim())

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="zadanie", description="Квест"),
        BotCommand(command="grow", description="Растить"),
        BotCommand(command="cd", description="Кулдауны"),
        BotCommand(command="status", description="Стата"),
        BotCommand(command="fight", description="Драка"),
        BotCommand(command="casino", description="Казик"),
        BotCommand(command="race", description="Гонки"),
        BotCommand(command="roulette", description="Рулетка"),
        BotCommand(command="steal", description="Украсть"),
        BotCommand(command="top", description="Топ-100"),
        BotCommand(command="top_group", description="Топ чата"),
        BotCommand(command="oldes", description="Олды"),
        BotCommand(command="info", description="Инфо")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
