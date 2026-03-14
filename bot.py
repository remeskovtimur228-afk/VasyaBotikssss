import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery

# ТВОЙ ТОКЕН
TOKEN = "8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs"
ADMIN_ID = 8443511218 # ID БАТИ (@sertof)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- СИСТЕМА БЛОКИРОВОК (ЗАЩИТА ОТ ДАБЛКЛИКОВ И АБУЗА) ---
user_locks = {}

def get_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

# --- МОМЕНТАЛЬНЫЙ КЭШ КУЛДАУНОВ (АНТИ-СПАМ) ---
cooldown_cache = {}
task_cache = {}

def is_on_cooldown(user_id, command_name, db_last_time_str, cooldown_hours):
    now = datetime.now()
    # 1. Сверхбыстрая проверка в оперативке (защита от автокликеров)
    if user_id in cooldown_cache and command_name in cooldown_cache[user_id]:
        if now < cooldown_cache[user_id][command_name] + timedelta(hours=cooldown_hours):
            return True
            
    # 2. Проверка в базе данных
    if db_last_time_str:
        db_time = datetime.fromisoformat(db_last_time_str)
        if now < db_time + timedelta(hours=cooldown_hours):
            return True
            
    return False

def set_cooldown_cache(user_id, command_name):
    if user_id not in cooldown_cache:
        cooldown_cache[user_id] = {}
    cooldown_cache[user_id][command_name] = datetime.now()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('vasya_hell_final.db')
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_members (chat_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, user_id))''')
    
    new_cols = [
        ("last_roulette", "TEXT"),
        ("last_steal", "TEXT"),
        ("display_name", "TEXT"),
        ("invited_by", "INTEGER")
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
    
    is_new = False
    if not res:
        cursor.execute("INSERT INTO users (user_id, username, display_name, size) VALUES (?, ?, ?, 0)", (uid, name, display_name))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
        is_new = True
    else:
        try:
            cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, uid))
            conn.commit()
        except:
            pass

    conn.close()
    return list(res), is_new

def update_u(uid, **kwargs):
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
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

# --- ГЕНЕРАТОРЫ ХУЕПЛЕТСТВА (ТЫСЯЧИ КОМБИНАЦИЙ) ---
INSULTS = [
    "хуеплёт", "пидорас", "уебище", "сын шлюхи", "выкидыш", "дристун", 
    "хуесос", "нищеброд", "ебло завали", "мразь", "чушка ебаная", "анальное отверстие",
    "шлепок майонезный", "ошибка презерватива", "глотатель", "защеканец", "петушара",
    "чепуха", "кусок долбоеба", "спермоглот", "шнырь", "животное", "биомусор"
]

def get_random_reply():
    p1 = ["Чё те надо, псина?", "Ебало завали, я занят.", "Хули ты меня тегаешь, задрот?", "Пошел нахуй отсюда.", "Иди поспи, дурачок."]
    p2 = ["Твоя мамка просила передать, что ты приемный.", "Иди /grow нажимай, у тебя там минус в штанах.", "Я тебя по IP вычислю и обоссу."]
    p3 = ["Завали свой хлебоприемник.", "Ебать ты оригинальный (нет).", "Твой IQ равен твоему размеру — он отрицательный."]
    return random.choice(p1 + p2 + p3 + INSULTS)

def get_task():
    acts = ["Высоси", "Оближи", "Засунь в очко", "Схавай", "Обоссы", "Прокукарекай", "Подожги", "Пни в ебало", "Станцуй стриптиз", "Отсоси у"]
    objs = ["дохлую крысу", "стакан мочи", "колесо трактора", "башмак соседа", "кактус", "грязную тряпку", "кусок говна", "бомжа"]
    locs = ["у ментовки", "перед батей", "в прямом эфире", "в одних трусах", "под гимн России", "на могиле своего достоинства", "на Красной площади"]
    return f"<b>{random.choice(acts)} {random.choice(objs)} {random.choice(locs)}!</b>"

# --- МИДЛВАРЬ ДЛЯ ЧАТОВ ---
class ChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if getattr(event, "chat", None) and event.chat.type in ['group', 'supergroup']:
            conn = sqlite3.connect('vasya_hell_final.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (event.chat.id,))
            if getattr(event, "from_user", None):
                cursor.execute("INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)", (event.chat.id, event.from_user.id))
            conn.commit()
            conn.close()
        return await handler(event, data)

dp.message.middleware(ChatMiddleware())

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ КУЛДАУНОВ ---
def get_cd_text(user_id, command_name, db_last_time_str, hours_cd):
    now = datetime.now()
    dt = None
    
    # Берем время из кэша, если есть (оно самое точное), иначе из БД
    if user_id in cooldown_cache and command_name in cooldown_cache[user_id]:
        dt = cooldown_cache[user_id][command_name]
    elif db_last_time_str:
        dt = datetime.fromisoformat(db_last_time_str)
        
    if dt:
        if dt + timedelta(hours=hours_cd) > now:
            rem = (dt + timedelta(hours=hours_cd)) - now
            return f"⏳ {int(rem.total_seconds() // 3600)}ч {int((rem.total_seconds() % 3600) // 60)}м"
    return "✅ Готово"

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(CommandStart())
async def start(m: types.Message):
    log_command()
    u, is_new = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    # Реферальная система
    args = m.text.split()
    if len(args) > 1 and is_new:
        try:
            ref_id = int(args[1])
            if ref_id != m.from_user.id:
                update_u(m.from_user.id, invited_by=ref_id)
                ref_u, _ = get_u(ref_id, "Unknown")
                update_u(ref_id, size=round(ref_u[2] + 0.3, 2))
                try:
                    await bot.send_message(ref_id, f"🤝 <b>ОПА!</b> Какой-то лох зашел по твоей ссылке! Тебе начислено <b>+0.3 см</b>.")
                except:
                    pass
        except ValueError:
            pass

    # Live-уведомление админу
    if is_new:
        try:
            await bot.send_message(ADMIN_ID, f"🔔 <b>НОВАЯ ЖЕРТВА:</b> {m.from_user.full_name} (@{m.from_user.username}) зашел в бота.")
        except:
            pass

    await m.reply(
        f"Здорово, {random.choice(INSULTS)}! Я Вася. \n\n"
        f"⚠️ <b>ВАЖНО:</b> Всё, что я тут несу — это <b>ЮМОР</b>. Я не хочу тебя обидеть, я просто так шучу, еблан. \n\n"
        f"Твоя реф. ссылка для приглашения лохов (дает +0.3 см тебе сразу):\n"
        f"<code>https://t.me/{(await bot.me()).username}?start={m.from_user.id}</code>\n\n"
        f"Меня состряпал @sertof. Будем мериться хуями или ты сразу нахуй пойдешь?"
    )

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    log_command()
    await m.reply(
        "<b>ЧИТАЙ, ПОКА Я ТЕБЕ ЕБАЛО НЕ ВСКРЫЛ:</b>\n\n"
        "<u>/zadanie</u> — Ебанутый квест (раз в день)\n"
        "<u>/grow</u> — Попытка вырасти (20ч кулдаун)\n"
        "<u>/status</u> — Твоя дырявая статистика\n"
        "<u>/cd</u> — Посмотреть свои кулдауны\n"
        "<u>/fight</u> — Пизделовка\n"
        "<u>/casino</u> — Слить в минус (раз в 1 час)\n"
        "<u>/race</u> — Уличные гонки (20ч кулдаун)\n"
        "<u>/roulette</u> — Русская рулетка (2ч кулдаун)\n"
        "<u>/steal</u> — Спиздить у лоха (4ч кулдаун)\n"
        "<u>/buy</u> — Купить см за Звезды (донат)\n"
        "<u>/top</u> — Глобальный топ 100 гигантов\n"
        "<u>/grouptop</u> — Топ пидорасов этой группы\n"
        "<u>/oldes</u> — Самые старые деды бота\n"
        "<u>/info</u> — Чё это за свалка\n\n"
        f"🙏 <i>Это рофл. Не принимай близко к сердцу, {random.choice(INSULTS)}.</i>"
    )

@dp.message(Command("info"))
async def info_cmd(m: types.Message):
    log_command()
    await m.reply(
        "ℹ️ <b>ИНФА ДЛЯ ТУПЫХ И ОБИДЧИВЫХ:</b>\n\n"
        "Слушай сюда, кусок дегенерата. Этот бот создан <b>ИСКЛЮЧИТЕЛЬНО</b> ради черного юмора, рофла и разъеба в кругу друзей.\n"
        "Мы никого не хотим оскорбить по-настоящему. Вся агрессия, маты и хуеплетство — это образ Васи, ебаного социопата.\n\n"
        "Создатель этого дурдома: @sertof. Жаловаться маме, а не ему."
    )

@dp.message(Command("cd", "cooldowns"))
async def cooldowns_cmd(m: types.Message):
    log_command()
    u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT last_roulette, last_steal FROM users WHERE user_id = ?", (u[0],))
    row = cursor.fetchone()
    conn.close()

    text = f"⏱ <b>ТВОИ ОТКАТЫ, {random.choice(INSULTS).upper()}:</b>\n\n"
    text += f"🍆 <b>Grow (20ч):</b> {get_cd_text(u[0], 'grow', u[3], 20)}\n"
    text += f"🏎 <b>Гонки (20ч):</b> {get_cd_text(u[0], 'race', u[7], 20)}\n"
    text += f"🎰 <b>Казино (1ч):</b> {get_cd_text(u[0], 'casino', u[8], 1)}\n"
    text += f"🔫 <b>Рулетка (2ч):</b> {get_cd_text(u[0], 'roulette', row[0] if row else None, 2)}\n"
    text += f"🥷 <b>Спиздить (4ч):</b> {get_cd_text(u[0], 'steal', row[1] if row else None, 4)}\n"
    
    await m.reply(text)

@dp.message(Command("zadanie"))
async def zadanie(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        now = str(datetime.now().date())
        
        # Моментальный кэш
        if m.from_user.id in task_cache and task_cache[m.from_user.id] == now:
            return await m.reply(f"Ты уже получал задание сегодня, {random.choice(INSULTS)}. Иди выполняй!")
            
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        if u[5] == now:
            task_cache[m.from_user.id] = now
            return await m.reply(f"Хули ты ноешь, {random.choice(INSULTS)}? Твоё ебаное задание: <i>{u[6]}</i>. Иди делай, сука!")
        
        t = get_task()
        task_cache[m.from_user.id] = now
        update_u(m.from_user.id, last_task=now, current_task=t)
        await m.reply(f"Слушай сюда, {random.choice(INSULTS)}. Твой квест:\n\n🔥 {t}\n\n<b>Не сделаешь — я твою родословную на хую вертел.</b>")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        
        # ЖЕЛЕЗОБЕТОННАЯ ПРОВЕРКА
        if is_on_cooldown(m.from_user.id, "grow", u[3], 20):
            return await m.reply(f"Куда лезешь, {random.choice(INSULTS)}?! Твой вялый еще не остыл. Чекай /cd.")
            
        # МОМЕНТАЛЬНАЯ БЛОКИРОВКА ДО ЗАПИСИ В БД
        set_cooldown_cache(m.from_user.id, "grow")
        
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
    u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм хуй" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ ПИДОРАС"
    disp = m.from_user.username if m.from_user.username else m.from_user.full_name
    await m.reply(f"📊 <b>ТВОЁ ДОСЬЕ ГОВНОЕДА ({disp}):</b>\n\n"
                  f"Длина: <i>{s} см</i>\n"
                  f"Ранг: <u>{r}</u>\n"
                  f"Ты по жизни: <i>{random.choice(INSULTS)}</i>")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
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
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        
        # ЖЕЛЕЗОБЕТОННАЯ ПРОВЕРКА
        if is_on_cooldown(m.from_user.id, "race", u[7], 20):
            return await m.reply(f"Твоя колымага еще на свалке. Чекай /cd, {random.choice(INSULTS)}.")

        # БЛОКИРУЕМ
        set_cooldown_cache(m.from_user.id, "race")

        msg = await m.reply("🏎 <b>Заезд пошел... Моча летит из окон...</b>")
        await asyncio.sleep(2)
        if random.random() > 0.6:
            update_u(u[0], size=round(u[2]+0.7, 2), last_race=datetime.now().isoformat())
            await bot.edit_message_text(f"🏁 Первое место! +0.7 см. Ты едешь быстрее, чем твоя мамка в кровать к соседу.", chat_id=m.chat.id, message_id=msg.message_id)
        else:
            update_u(u[0], size=round(u[2]-1.0, 2), last_race=datetime.now().isoformat())
            await bot.edit_message_text(f"💩 Ты врезался в фуру с навозом. -1.0 см. Лох ебаный.", chat_id=m.chat.id, message_id=msg.message_id)

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        
        if is_on_cooldown(m.from_user.id, "casino", u[8], 1):
            return await m.reply(f"Куда ты лезешь со своими копейками, {random.choice(INSULTS)}? Казик закрыт. Чекай /cd.")

        set_cooldown_cache(m.from_user.id, "casino")

        if random.random() > 0.8:
            update_u(u[0], size=round(u[2]+3.5, 2), last_casino=datetime.now().isoformat())
            await m.reply(f"🎰 <b>СУКА, ПОВЕЗЛО!</b> +3.5 см. Проваливай, пока я тебя не прирезал.")
        else:
            update_u(u[0], size=round(u[2]-2.5, 2), last_casino=datetime.now().isoformat())
            await m.reply(f"🎰 <b>ЗЕРО, ЕБЛАН!</b> -2.5 см. Ты теперь официально должен мне свой анус.")

@dp.message(Command("roulette"))
async def roulette(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        
        conn = sqlite3.connect('vasya_hell_final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT last_roulette FROM users WHERE user_id = ?", (u[0],))
        row = cursor.fetchone()
        conn.close()
        
        last_r = row[0] if row else None
        
        if is_on_cooldown(m.from_user.id, "roulette", last_r, 2):
            return await m.reply(f"Ствол перегрелся, дегенерат. Чекай /cd.")

        set_cooldown_cache(m.from_user.id, "roulette")

        msg = await m.reply("🔫 <b>Крутишь барабан, приставляешь к виску...</b>")
        await asyncio.sleep(1.5)
        
        update_u(u[0], last_roulette=datetime.now().isoformat())
        
        if random.random() < 0.16: 
            loss = round(random.uniform(2.0, 5.0), 2)
            update_u(u[0], size=round(u[2]-loss, 2))
            await bot.edit_message_text(f"💥 <b>ВЫСТРЕЛ!</b> Мозги на стене. Твой хуй отсох на <b>{loss} см</b>.", chat_id=m.chat.id, message_id=msg.message_id)
        else:
            win = round(random.uniform(0.3, 1.0), 2)
            update_u(u[0], size=round(u[2]+win, 2))
            await bot.edit_message_text(f"💨 <b>Щелчок...</b> Пронесло, {random.choice(INSULTS)}. На радостях вырос на <b>{win} см</b>.", chat_id=m.chat.id, message_id=msg.message_id)

@dp.message(Command("steal"))
async def steal(m: types.Message):
    log_command()
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        
        conn = sqlite3.connect('vasya_hell_final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT last_steal FROM users WHERE user_id = ?", (u[0],))
        row = cursor.fetchone()
        
        last_s = row[0] if row else None
        
        if is_on_cooldown(m.from_user.id, "steal", last_s, 4):
            conn.close()
            return await m.reply(f"Ты еще от прошлой кражи не отмылся, шнырь. Чекай /cd.")

        set_cooldown_cache(m.from_user.id, "steal")

        cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u[0],))
        target = cursor.fetchone()
        conn.close()

        if not target:
            return await m.reply("Тут некого грабить, ты один на районе как лох.")

        update_u(u[0], last_steal=datetime.now().isoformat())

        if random.random() > 0.6: 
            stolen = round(random.uniform(0.2, 1.2), 2)
            update_u(u[0], size=round(u[2]+stolen, 2))
            update_u(target[0], size=round(target[2]-stolen, 2))
            await m.reply(f"🥷 <b>ТЫ КРАСАВА!</b> Подрезал у {target[1]} целых <b>{stolen} см</b>!")
            
            try:
                await bot.send_message(target[0], f"🚨 <b>АЛАРМ, ЕПТА!</b> Какая-то крыса ({u[2]} или как его там) спиздила у тебя <b>{stolen} см</b> пока ты спал!")
            except:
                pass
        else:
            fail = round(random.uniform(0.5, 1.5), 2)
            update_u(u[0], size=round(u[2]-fail, 2))
            await m.reply(f"🚨 <b>ПОПАЛСЯ!</b> {target[1]} поймал тебя за руку и оторвал <b>{fail} см</b>. Позорище.")

@dp.message(Command("top"))
async def top(m: types.Message):
    log_command()
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, size FROM users WHERE size != 0 ORDER BY size DESC LIMIT 100")
    rows = cursor.fetchall()
    
    text = "🌍 <b>ГЛОБАЛЬНЫЙ ТОП 100 (ОТ ГИГАНТОВ ДО МИНУСОВ):</b>\n\n"
    for i, r in enumerate(rows, 1):
        name = r[0] if r[0] else "Какой-то лох"
        text += f"{i}. {name} — <b>{r[1]} см</b>\n"
    
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await m.reply(text[x:x+4000])
    else:
        await m.reply(text)
    conn.close()

@dp.message(Command("grouptop"))
async def grouptop(m: types.Message):
    log_command()
    if m.chat.type not in ['group', 'supergroup']:
        return await m.reply("Эта хуйня работает только в группах, еблан!")
        
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.display_name, u.size 
                      FROM users u 
                      JOIN chat_members cm ON u.user_id = cm.user_id 
                      WHERE cm.chat_id = ? AND u.size != 0 
                      ORDER BY u.size DESC LIMIT 50''', (m.chat.id,))
    rows = cursor.fetchall()
    
    text = "🏘 <b>ТОП ПИДОРАСОВ ЭТОЙ ГРУППЫ:</b>\n\n"
    if not rows:
        text += "Тут одни нули."
    else:
        for i, r in enumerate(rows, 1):
            name = r[0] if r[0] else "Лох"
            text += f"{i}. {name} — <b>{r[1]} см</b>\n"
            
    await m.reply(text)
    conn.close()

@dp.message(Command("oldes"))
async def oldes(m: types.Message):
    log_command()
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, size FROM users ORDER BY user_id ASC LIMIT 20")
    rows = cursor.fetchall()
    
    text = "👴 <b>САМЫЕ СТАРЫЕ ДЕДЫ ЭТОГО БОТА:</b>\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} (<i>{r[1]} см</i>)\n"
    await m.reply(text)
    conn.close()

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
    async with get_lock(m.from_user.id):
        u, _ = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
        update_u(m.from_user.id, size=round(u[2] + 0.5, 2))
        await m.reply(f"🤑 <b>ОПЛАЧЕНО!</b> Твои жалкие Звезды ушли в фонд Васи. Тебе начислено <b>+0.5 см</b>. Будь счастлив, мажор хуев.")

# --- АДМИН ПАНЕЛЬ ДЛЯ @sertof ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.reply(f"Пошел нахуй отсюда. Ты не @sertof, {random.choice(INSULTS)}.")
    
    conn = sqlite3.connect('vasya_hell_final.db')
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
        "Твои админские права:\n"
        "<code>/sendall [текст]</code> - Рассылка всем\n"
        "<code>/give_cm [ID] [число]</code> - Выдать см\n"
        "<code>/take_cm [ID] [число]</code> - Забрать см"
    )

@dp.message(Command("give_cm"))
async def admin_give(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) < 3: return await m.reply("Формат: /give_cm [ID] [число]")
    try:
        uid = int(args[1])
        amount = float(args[2])
        u, _ = get_u(uid, "Unknown")
        update_u(uid, size=round(u[2] + amount, 2))
        await m.reply(f"✅ Успешно выдано {amount} см пидорасу {uid}.")
    except Exception as e:
        await m.reply(f"Ошибка: {e}")

@dp.message(Command("take_cm"))
async def admin_take(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) < 3: return await m.reply("Формат: /take_cm [ID] [число]")
    try:
        uid = int(args[1])
        amount = float(args[2])
        u, _ = get_u(uid, "Unknown")
        update_u(uid, size=round(u[2] - amount, 2))
        await m.reply(f"✅ Успешно отнято {amount} см у пидораса {uid}.")
    except Exception as e:
        await m.reply(f"Ошибка: {e}")

@dp.message(Command("sendall"))
async def admin_sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.reply(f"Пшел вон, {random.choice(INSULTS)}, это кнопка для бати.")
    
    text = m.text.replace("/sendall", "").strip()
    if not text:
        return await m.reply("Бля, батя, текст забыл написать.")
    
    users = get_all_users()
    chats = get_all_chats()
    
    targets = list(set(users + chats))
    count = 0
    
    await m.reply(f"Начинаю ебашить ковровую бомбардировку по {len(targets)} целям (ЛС + Группы)...")
    
    for target_id in targets:
        try:
            await bot.send_message(target_id, f"📢 <b>ПОСЛАНИЕ ОТ БАТИ (@sertof):</b>\n\n{text}")
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            pass 
            
    await m.reply(f"✅ Рассылка завершена. Успешно дошло до {count} уебков/чатов.")

# --- РАНДОМНЫЕ НАЕЗДЫ И ОТВЕТЫ В ЧАТАХ ---
@dp.message()
async def auto_insult(m: types.Message):
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    text = m.text.lower() if m.text else ""
    
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.id
    is_mentioned = "вася" in text or f"@{bot.id}" in text

    if is_reply or is_mentioned:
        return await m.reply(get_random_reply())
    
    if m.chat.type in ['group', 'supergroup']:
        rand_val = random.random()
        if rand_val < 0.02 and m.text:
            mock_text = "".join(c.upper() if random.choice([True, False]) else c.lower() for c in m.text)
            await m.reply(f"<i>«{mock_text}»</i> — ебать ты умный.")
        elif rand_val < 0.06: 
            await m.reply(f"Слышь, {random.choice(INSULTS)}, хули ты тут расписался? Иди лучше /grow жми.")
        elif rand_val < 0.07:
            await m.answer(f"Скучно с вами, пидорасы. Кто первым напишет <code>Вася батя</code>, тому накину +1 см.")

async def main():
    init_db()
    
    try:
        await bot.set_my_description("Здорово, еблан! Я Вася. Жми СТАРТ и готовь очко к пиздецу.")
    except:
        pass

    await bot.set_my_commands([
        BotCommand(command="zadanie", description="Ебаный квест"),
        BotCommand(command="grow", description="Растить хуйню (20ч)"),
        BotCommand(command="status", description="Твоё дно"),
        BotCommand(command="cd", description="Посмотреть кулдауны"),
        BotCommand(command="fight", description="Пизделовка"),
        BotCommand(command="casino", description="Казик (1ч)"),
        BotCommand(command="race", description="Гонки (20ч)"),
        BotCommand(command="roulette", description="Рулетка (2ч)"),
        BotCommand(command="steal", description="Спиздить см (4ч)"),
        BotCommand(command="buy", description="Купить см (Звезды)"),
        BotCommand(command="top", description="Глобальный Топ 100"),
        BotCommand(command="grouptop", description="Топ этой группы"),
        BotCommand(command="oldes", description="Самые старые юзеры"),
        BotCommand(command="info", description="Справка для нытиков")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
