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

# ВПИШИ СЮДА ИМЯ СВОЕЙ СТАРОЙ БАЗЫ, ЕСЛИ ОНО БЫЛО ДРУГИМ!
DB_NAME = 'vasya_hell_final.db' 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
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
    cursor = conn.cursor()
    today = str(datetime.now().date())
    cursor.execute("INSERT OR IGNORE INTO command_stats (date, count) VALUES (?, 0)", (today,))
    cursor.execute("UPDATE command_stats SET count = count + 1 WHERE date = ?", (today,))
    conn.commit()
    conn.close()

def get_u(uid, name=None, uname=None):
    conn = sqlite3.connect(DB_NAME)
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
        try:
            cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, uid))
            conn.commit()
        except: pass
    conn.close()
    return list(res)

def update_u(uid, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for k, v in kwargs.items():
        cursor.execute(f"UPDATE users SET {k} = ? WHERE user_id = ?", (v, uid))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def get_all_chats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM chats")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

# --- ТВОИ ОРИГИНАЛЬНЫЕ ГЕНЕРАТОРЫ ХУЕПЛЕТСТВА (ВЕРНУЛ ВСЁ ДО КАПЛИ) ---
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

# --- MIDDLEWARE ДЛЯ ЧАТОВ И СТАТИСТИКИ ---
class ChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if getattr(event, "chat", None) and event.chat.type in ['group', 'supergroup']:
            cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (event.chat.id,))
            if getattr(event, "from_user", None):
                cursor.execute("INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)", (event.chat.id, event.from_user.id))
        
        if getattr(event, "from_user", None):
            u_id = event.from_user.id
            u_name = event.from_user.full_name
            u_uname = event.from_user.username
            disp = f"@{u_uname}" if u_uname else u_name
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username, display_name, size) VALUES (?, ?, ?, 0)", (u_id, u_name, disp))
            cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (disp, u_id))
        
        conn.commit()
        conn.close()
        return await handler(event, data)

dp.message.middleware(ChatMiddleware())

# --- ОБРАБОТЧИКИ КОМАНД ---

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
    await m.reply(
        "ℹ️ <b>ИНФА ДЛЯ ТУПЫХ И ОБИДЧИВЫХ:</b>\n\n"
        "Слушай сюда, кусок дегенерата. Этот бот создан <b>ИСКЛЮЧИТЕЛЬНО</b> ради черного юмора, рофла и разъеба в кругу друзей.\n"
        "Мы никого не хотим оскорбить по-настоящему. Вся агрессия, маты и хуеплетство — это образ Васи, ебаного социопата.\n\n"
        "🛑 <b>ВАЖНЫЕ ПРАВИЛА:</b>\n"
        "1. Пизделовка (/fight) — БЕСКОНЕЧНА. Но шанс выиграть там пиздец какой маленький. Это сделано специально, чтобы ты страдал.\n"
        "2. Задания (/zadanie) — это НЕ официальная игра, а просто тупой рофл для развлечения. Можешь выполнять, можешь забить хуй, мы ни к чему не призываем.\n"
        "3. Вася <b>НЕ УМЕЕТ</b> управлять группами, банить или удалять сообщения. Он тут просто чтобы срать в чат и мериться с вами вымышленными писюнами.\n\n"
        "Создатель этого дурдома: @sertof. Жаловаться маме, а не ему."
    )

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
        await m.reply(f"Слушай сюда, {random.choice(INSULTS)}. Твой квест:\n\n🔥 {t}\n\n<b>Не сделаешь — я твою родословную на хую вертел.</b>")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[3] and datetime.fromisoformat(u[3]) > datetime.now() - timedelta(hours=20):
        return await m.reply(f"Куда лезешь, {random.choice(INSULTS)}?! Твой вялый еще не остыл. Жди 20 часов.")
    
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[2] + change, 2) 
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    
    if change > 0: 
        await m.reply(f"Опа, {random.choice(INSULTS)}. Подрос на <b>{change} см</b>. Теперь: <u>{new_s} см</u>.")
    else: 
        await m.reply(f"ХА-ХА-ХА! Ты так старался, что он ушел внутрь на <b>{abs(change)} см</b>. Твой долг миру: <u>{new_s} см</u>.")

@dp.message(Command("status"))
async def status(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм хуй" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ ПИДОРАС"
    disp = m.from_user.username if m.from_user.username else m.from_user.full_name
    await m.reply(f"📊 <b>ТВОЁ ДОСЬЕ ГОВНОЕДА ({disp}):</b>\n\nДлина: <i>{s} см</i>\nРанг: <u>{r}</u>\nТы по жизни: <i>{random.choice(INSULTS)}</i>")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if random.random() > 0.95:
        win = round(random.uniform(1.0, 3.5), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.reply(f"🤜 <b>ПИЗДЕЦ НЕМЫСЛИМЫЙ!</b> Ты вырубил быка (шанс был мизерный). Лови <b>+{win} см</b>. Но ты всё равно {random.choice(INSULTS)}.")
    else:
        loss = round(random.uniform(0.6, 2.5), 2)
        update_u(u[0], size=round(u[2]-loss, 2)) 
        await m.reply(f"💀 <b>ФИАСКО!</b> Тебя изнасиловали за гаражами. Минус <b>{loss} см</b>.")

@dp.message(Command("race"))
async def race(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[7] and datetime.fromisoformat(u[7]) > datetime.now() - timedelta(hours=20):
        return await m.reply(f"Твоя колымага еще на свалке. Жди 20 часов, {random.choice(INSULTS)}.")

    await m.reply("🏎 <b>Заезд пошел... Моча летит из окон...</b>")
    await asyncio.sleep(2)
    if random.random() > 0.6:
        update_u(u[0], size=round(u[2]+0.7, 2), last_race=datetime.now().isoformat())
        await bot.send_message(m.chat.id, f"🏁 Первое место! +0.7 см. Ты едешь быстрее, чем твоя мамка в кровать к соседу.", reply_to_message_id=m.message_id)
    else:
        update_u(u[0], size=round(u[2]-1.0, 2), last_race=datetime.now().isoformat())
        await bot.send_message(m.chat.id, f"💩 Ты врезался в фуру с навозом. -1.0 см. Лох ебаный.", reply_to_message_id=m.message_id)

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[8] and datetime.fromisoformat(u[8]) > datetime.now() - timedelta(hours=1):
        diff = datetime.fromisoformat(u[8]) + timedelta(hours=1) - datetime.now()
        minutes = int(diff.total_seconds() // 60)
        return await m.reply(f"Куда ты лезешь со своими копейками, {random.choice(INSULTS)}? Казик закрыт. Приходи через {minutes} мин.")

    if random.random() > 0.8:
        update_u(u[0], size=round(u[2]+3.5, 2), last_casino=datetime.now().isoformat())
        await m.reply(f"🎰 <b>СУКА, ПОВЕЗЛО!</b> +3.5 см. Проваливай, пока я тебя не прирезал.")
    else:
        update_u(u[0], size=round(u[2]-2.5, 2), last_casino=datetime.now().isoformat())
        await m.reply(f"🎰 <b>ЗЕРО, ЕБЛАН!</b> -2.5 см. Ты теперь официально должен мне свой анус.")

@dp.message(Command("roulette"))
async def roulette(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[9] and datetime.fromisoformat(u[9]) > datetime.now() - timedelta(hours=2):
        return await m.reply(f"Ствол перегрелся, дегенерат. Жди 2 часа.")

    await m.reply("🔫 <b>Крутишь барабан, приставляешь к виску...</b>")
    await asyncio.sleep(1.5)
    update_u(u[0], last_roulette=datetime.now().isoformat())
    
    if random.random() < 0.16:
        loss = round(random.uniform(2.0, 5.0), 2)
        update_u(u[0], size=round(u[2]-loss, 2))
        await bot.send_message(m.chat.id, f"💥 <b>ВЫСТРЕЛ!</b> Мозги на стене. Твой хуй отсох на <b>{loss} см</b>.", reply_to_message_id=m.message_id)
    else:
        win = round(random.uniform(0.3, 1.0), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await bot.send_message(m.chat.id, f"💨 <b>Щелчок...</b> Пронесло, {random.choice(INSULTS)}. На радостях вырос на <b>{win} см</b>.", reply_to_message_id=m.message_id)

@dp.message(Command("steal"))
async def steal(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[10] and datetime.fromisoformat(u[10]) > datetime.now() - timedelta(hours=4):
        return await m.reply(f"Ты еще от прошлой кражи не отмылся, шнырь. Жди 4 часа.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? AND size != 0 ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = cursor.fetchone()
    conn.close()

    if not target: return await m.reply("Тут некого грабить, ты один на районе как лох.")

    update_u(u[0], last_steal=datetime.now().isoformat())

    if random.random() > 0.6: 
        stolen = round(random.uniform(0.2, 1.2), 2)
        update_u(u[0], size=round(u[2]+stolen, 2))
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.reply(f"🥷 <b>ТЫ КРАСАВА!</b> Подрезал у {target[1]} целых <b>{stolen} см</b>!")
        try: await bot.send_message(target[0], f"🚨 <b>АХТУНГ!</b> {u[11]} спиздил у тебя <b>{stolen} см</b> пока ты спал!")
        except: pass
    else:
        fail = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[2]-fail, 2))
        await m.reply(f"🚨 <b>ПОПАЛСЯ!</b> {target[1]} поймал тебя за руку и оторвал <b>{fail} см</b>. Позорище.")

@dp.message(Command("top"))
async def top(m: types.Message):
    log_command()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, size FROM users WHERE size != 0 ORDER BY size DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    
    text = "🌍 <b>ГЛОБАЛЬНЫЙ ТОП-100:</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    
    if len(text) > 4000:
        await m.reply(text[:4000] + "\n...и остальные обрыганы.")
    else:
        await m.reply(text)

@dp.message(Command("top_group"))
async def top_group(m: types.Message):
    log_command()
    if m.chat.type == 'private': return await m.reply("Это только для групп, еблан.")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.display_name, u.size 
        FROM users u 
        JOIN chat_members c ON u.user_id = c.user_id 
        WHERE c.chat_id = ? AND u.size != 0 
        ORDER BY u.size DESC LIMIT 50
    """, (m.chat.id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows: return await m.reply("В этой помойке ни у кого нет размера.")
    
    text = f"🏠 <b>ТОП ЭТОГО ЧАТА:</b>\n\n"
    for i, r in enumerate(rows, 1): text += f"{i}. {r[0]} — <b>{r[1]} см</b>\n"
    await m.reply(text)

@dp.message(Command("oldes"))
async def oldes(m: types.Message):
    log_command()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT display_name FROM users ORDER BY rowid ASC LIMIT 15")
    rows = cursor.fetchall()
    conn.close()
    
    text = "🦴 <b>ОЛДЫ БОТА (Деды):</b>\n\n"
    for i, r in enumerate(rows, 1): text += f"{i}. {r[0]}\n"
    await m.reply(text)

@dp.message(Command("buy"))
async def buy_stars(m: types.Message):
    log_command()
    await bot.send_invoice(
        chat_id=m.chat.id,
        title="Удлинить огрызок",
        description="Покупка 0.5 см за 15 Telegram Stars. Официальный донат Васе на пиво.",
        payload="buy_05_cm",
        provider_token="", 
        currency="XTR",
        prices=[LabeledPrice(label="0.5 сантиметра чести", amount=15)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pcq.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    update_u(m.from_user.id, size=round(u[2] + 0.5, 2))
    await m.reply(f"🤑 <b>ОПЛАЧЕНО!</b> Твои жалкие Звезды ушли в фонд Васи. Тебе начислено <b>+0.5 см</b>. Будь счастлив, мажор хуев.")

# --- КОМАНДЫ ДЛЯ БАТИ (@sertof) ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return await m.reply(f"Пошел нахуй отсюда. Ты не @sertof, {random.choice(INSULTS)}.")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    chats_count = cursor.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    today = str(datetime.now().date())
    this_month = today[:7] + '%'
    this_year = today[:4] + '%'
    
    day_cmds = cursor.execute("SELECT count FROM command_stats WHERE date = ?", (today,)).fetchone()
    day_cmds = day_cmds[0] if day_cmds else 0
    month_cmds = cursor.execute("SELECT SUM(count) FROM command_stats WHERE date LIKE ?", (this_month,)).fetchone()
    month_cmds = month_cmds[0] if month_cmds[0] else 0
    year_cmds = cursor.execute("SELECT SUM(count) FROM command_stats WHERE date LIKE ?", (this_year,)).fetchone()
    year_cmds = year_cmds[0] if year_cmds[0] else 0
    conn.close()
    
    await m.reply(
        "👑 <b>СЛАВА ВЕЛИКОМУ @sertof!</b>\n\n"
        "Слушаюсь и повинуюсь, мой господин.\n\n"
        "📊 <b>СТАТИСТИКА БОТА:</b>\n"
        f"👥 Лохов в базе: <b>{users_count}</b>\n"
        f"🌐 Групп, где мы срем: <b>{chats_count}</b>\n"
        f"⚡ Команд за сегодня: <b>{day_cmds}</b>\n"
        f"📅 Команд за месяц: <b>{month_cmds}</b>\n"
        f"🌍 Команд за год: <b>{year_cmds}</b>\n\n"
        "🛠 <b>Управление:</b>\n"
        "<code>/sendall [текст]</code> — Рассылка\n"
        "<code>/give [id] [см]</code> — Выдать см\n"
        "<code>/take [id] [см]</code> — Забрать см"
    )

@dp.message(Command("give", "take"))
async def admin_give_take(m: types.Message, command: CommandObject):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id = int(args[0])
        amount = float(args[1])
        u = get_u(target_id)
        if not u: return await m.reply("Нет такого лоха в базе.")
        
        new_size = round(u[2] + amount if command.command == "give" else u[2] - amount, 2)
        update_u(target_id, size=new_size)
        await m.reply(f"✅ Батя сделал дело. Теперь у {u[11]} размер: {new_size} см.")
    except:
        await m.reply("Неправильно. Пиши: /give 123456789 5.5")

@dp.message(Command("sendall"))
async def admin_sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID: return await m.reply(f"Пшел вон, {random.choice(INSULTS)}, это кнопка для бати.")
    text = m.text.replace("/sendall", "").strip()
    if not text: return await m.reply("Бля, батя, текст забыл написать.")
    
    targets = list(set(get_all_users() + get_all_chats()))
    count = 0
    await m.reply(f"Начинаю ебашить ковровую бомбардировку по {len(targets)} целям (ЛС + Группы)...")
    for target_id in targets:
        try:
            await bot.send_message(target_id, f"📢 <b>ПОСЛАНИЕ ОТ БАТИ (@sertof):</b>\n\n{text}")
            count += 1
            await asyncio.sleep(0.05) 
        except: pass 
            
    await m.reply(f"✅ Рассылка завершена. Успешно дошло до {count} уебков/чатов.")

# --- АВТООТВЕТЫ И ПОВТОРЯШКА ---
@dp.message()
async def auto_handler(m: types.Message):
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    text = m.text.lower() if m.text else ""
    
    # Повторяшка (шанс 1% в группах)
    if m.chat.type in ['group', 'supergroup'] and m.text and random.random() < 0.01:
        await m.answer(m.text)
        return

    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.id
    is_mentioned = "вася" in text or f"@{bot.id}" in text

    if is_reply or is_mentioned:
        if random.random() > 0.5:
            return await m.reply(random.choice(MENTION_REPLIES))
        else:
            return await m.reply(random.choice(RANDOM_ANSWERS))
    
    if m.chat.type in ['group', 'supergroup'] and random.random() < 0.05: 
        await m.reply(get_claim())
        
    if m.chat.type in ['group', 'supergroup'] and random.random() < 0.01:
        await m.answer(f"Скучно с вами, пидорасы. Кто первым напишет <code>Вася батя</code>, тому накину +1 см.")

async def main():
    init_db()
    
    try:
        await bot.set_my_description("Здарова, уебище. Я Вася — бот для жестких рофлов и измерения хуев. \n\nЖми старт, если не зассал.")
        await bot.set_my_short_description("Бот от Бати (@sertof). Меримся хуями, грабим лохов.")
    except: pass 
    
    await bot.set_my_commands([
        BotCommand(command="zadanie", description="Ебаный квест"),
        BotCommand(command="grow", description="Растить (20ч)"),
        BotCommand(command="cd", description="Твои кулдауны"),
        BotCommand(command="status", description="Твоё дно"),
        BotCommand(command="fight", description="Пизделовка"),
        BotCommand(command="casino", description="Казик (1ч)"),
        BotCommand(command="race", description="Гонки (20ч)"),
        BotCommand(command="roulette", description="Рулетка (2ч)"),
        BotCommand(command="steal", description="Спиздить см (4ч)"),
        BotCommand(command="ref", description="Заработать на лохах"),
        BotCommand(command="buy", description="Купить см (Звезды)"),
        BotCommand(command="top", description="Глобальный Топ-100"),
        BotCommand(command="top_group", description="Топ этого чата"),
        BotCommand(command="oldes", description="Олды бота"),
        BotCommand(command="info", description="Справка")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
