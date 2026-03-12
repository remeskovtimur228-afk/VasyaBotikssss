import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery

# ТВОЙ ТОКЕН, СУКА
TOKEN = "8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs"
ADMIN_ID = 8443511218 # ID БАТИ (@sertof)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

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
    
    # ДОПОЛНЕНИЯ: Новые таблицы и колонки
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS command_stats (date TEXT PRIMARY KEY, count INTEGER DEFAULT 0)''')
    
    new_cols = [
        ("last_roulette", "TEXT"),
        ("last_steal", "TEXT"),
        ("display_name", "TEXT")
    ]
    for col, ctype in new_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass # Если колонка уже есть - похуй, едем дальше

    conn.commit()
    conn.close()

# Логгер команд для статы бати
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
    
    # Логика юзернейма
    display_name = f"@{uname}" if uname else name

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id, username, display_name, size) VALUES (?, ?, ?, 0)", (uid, name, display_name))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
    else:
        # Обновляем отображаемое имя, если чушпан его поменял
        try:
            cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, uid))
            conn.commit()
        except:
            pass

    conn.close()
    return list(res)

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

# --- НОРМАЛЬНАЯ МИДЛВАРЬ ДЛЯ ЧАТОВ (Чтоб команды сука работали) ---
class ChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Ловим ID чата, если это группа, записываем в базу и пускаем дальше
        if getattr(event, "chat", None) and event.chat.type in ['group', 'supergroup']:
            conn = sqlite3.connect('vasya_hell_final.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (event.chat.id,))
            conn.commit()
            conn.close()
        # Пропускаем к командам
        return await handler(event, data)

# Подключаем мидлварь к роутеру сообщений
dp.message.middleware(ChatMiddleware())

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def start(m: types.Message):
    log_command()
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)

    await m.answer(
        f"Здорово, {random.choice(INSULTS)}! Я Вася. \n\n"
        f"⚠️ <b>ВАЖНО:</b> Всё, что я тут несу — это <b>ЮМОР</b>. Я не хочу тебя обидеть, я просто так шучу, еблан. \n\n"
        f"Меня состряпал @sertof. Будем мериться хуями или ты сразу нахуй пойдешь?"
    )

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    log_command()
    await m.answer(
        "<b>ЧИТАЙ, ПОКА Я ТЕБЕ ЕБАЛО НЕ ВСКРЫЛ:</b>\n\n"
        "<u>/zadanie</u> — Ебанутый квест (раз в день)\n"
        "<u>/grow</u> — Попытка вырасти (20ч кулдаун)\n"
        "<u>/status</u> — Твоя дырявая статистика\n"
        "<u>/fight</u> — Пизделовка\n"
        "<u>/casino</u> — Слить в минус (раз в 1 час)\n"
        "<u>/race</u> — Уличные гонки (20ч кулдаун)\n"
        "<u>/roulette</u> — Русская рулетка (2ч кулдаун)\n"
        "<u>/steal</u> — Спиздить у лоха (4ч кулдаун)\n"
        "<u>/buy</u> — Купить см за Звезды (донат)\n"
        "<u>/top</u> — Топ тех, кто ебет тебя в жопу\n"
        "<u>/info</u> — Чё это за свалка\n\n"
        "🙏 <i>Это рофл. Не принимай близко к сердцу, {random.choice(INSULTS)}.</i>"
    )

@dp.message(Command("info"))
async def info_cmd(m: types.Message):
    log_command()
    await m.answer(
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
        await m.answer(f"Хули ты ноешь, {random.choice(INSULTS)}? Твоё ебаное задание: <i>{u[6]}</i>. Иди делай, сука!")
    else:
        t = get_task()
        update_u(m.from_user.id, last_task=now, current_task=t)
        await m.answer(f"Слушай сюда, {random.choice(INSULTS)}. Твой квест:\n\n🔥 {t}\n\n<b>Не сделаешь — я твою родословную на хую вертел.</b>")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[3] and datetime.fromisoformat(u[3]) > datetime.now() - timedelta(hours=20):
        await m.answer(f"Куда лезешь, {random.choice(INSULTS)}?! Твой вялый еще не остыл. Жди 20 часов.")
        return
    
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[2] + change, 2) 
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    
    if change > 0:
        await m.answer(f"Опа, {random.choice(INSULTS)}. Подрос на <b>{change} см</b>. Теперь: <u>{new_s} см</u>.")
    else:
        await m.answer(f"ХА-ХА-ХА! Ты так старался, что он ушел внутрь на <b>{abs(change)} см</b>. Твой долг миру: <u>{new_s} см</u>.")

@dp.message(Command("status"))
async def status(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм хуй" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ ПИДОРАС"
    disp = m.from_user.username if m.from_user.username else m.from_user.full_name
    await m.answer(f"📊 <b>ТВОЁ ДОСЬЕ ГОВНОЕДА ({disp}):</b>\n\n"
                   f"Длина: <i>{s} см</i>\n"
                   f"Ранг: <u>{r}</u>\n"
                   f"Ты по жизни: <i>{random.choice(INSULTS)}</i>")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if random.random() > 0.95: # 5% победы
        win = round(random.uniform(1.0, 3.5), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.answer(f"🤜 <b>ПИЗДЕЦ НЕМЫСЛИМЫЙ!</b> Ты вырубил быка (шанс был мизерный). Лови <b>+{win} см</b>. Но ты всё равно {random.choice(INSULTS)}.")
    else:
        loss = round(random.uniform(0.6, 2.5), 2)
        update_u(u[0], size=round(u[2]-loss, 2)) 
        await m.answer(f"💀 <b>ФИАСКО!</b> Тебя изнасиловали за гаражами. Минус <b>{loss} см</b>.")

@dp.message(Command("race"))
async def race(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[7] and datetime.fromisoformat(u[7]) > datetime.now() - timedelta(hours=20):
        await m.answer(f"Твоя колымага еще на свалке. Жди 20 часов, {random.choice(INSULTS)}.")
        return

    await m.answer("🏎 <b>Заезд пошел... Моча летит из окон...</b>")
    await asyncio.sleep(2)
    if random.random() > 0.6:
        update_u(u[0], size=round(u[2]+0.7, 2), last_race=datetime.now().isoformat())
        await m.answer(f"🏁 Первое место! +0.7 см. Ты едешь быстрее, чем твоя мамка в кровать к соседу.")
    else:
        update_u(u[0], size=round(u[2]-1.0, 2), last_race=datetime.now().isoformat())
        await m.answer(f"💩 Ты врезался в фуру с навозом. -1.0 см. Лох ебаный.")

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    if u[8] and datetime.fromisoformat(u[8]) > datetime.now() - timedelta(hours=1):
        diff = datetime.fromisoformat(u[8]) + timedelta(hours=1) - datetime.now()
        minutes = int(diff.total_seconds() // 60)
        await m.answer(f"Куда ты лезешь со своими копейками, {random.choice(INSULTS)}? Казик закрыт. Приходи через {minutes} мин.")
        return

    if random.random() > 0.8:
        update_u(u[0], size=round(u[2]+3.5, 2), last_casino=datetime.now().isoformat())
        await m.answer(f"🎰 <b>СУКА, ПОВЕЗЛО!</b> +3.5 см. Проваливай, пока я тебя не прирезал.")
    else:
        update_u(u[0], size=round(u[2]-2.5, 2), last_casino=datetime.now().isoformat())
        await m.answer(f"🎰 <b>ЗЕРО, ЕБЛАН!</b> -2.5 см. Ты теперь официально должен мне свой анус.")

# НОВАЯ ИГРА: Рулетка
@dp.message(Command("roulette"))
async def roulette(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT last_roulette FROM users WHERE user_id = ?", (u[0],))
    row = cursor.fetchone()
    conn.close()
    
    last_r = row[0] if row else None
    if last_r and datetime.fromisoformat(last_r) > datetime.now() - timedelta(hours=2):
        await m.answer(f"Ствол перегрелся, дегенерат. Жди 2 часа.")
        return

    await m.answer("🔫 <b>Крутишь барабан, приставляешь к виску...</b>")
    await asyncio.sleep(1.5)
    
    update_u(u[0], last_roulette=datetime.now().isoformat())
    
    if random.random() < 0.16: # 1/6 шанс проебать много
        loss = round(random.uniform(2.0, 5.0), 2)
        update_u(u[0], size=round(u[2]-loss, 2))
        await m.answer(f"💥 <b>ВЫСТРЕЛ!</b> Мозги на стене. Твой хуй отсох на <b>{loss} см</b>.")
    else:
        win = round(random.uniform(0.3, 1.0), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.answer(f"💨 <b>Щелчок...</b> Пронесло, {random.choice(INSULTS)}. На радостях вырос на <b>{win} см</b>.")

# НОВАЯ ИГРА: Воровство
@dp.message(Command("steal"))
async def steal(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT last_steal FROM users WHERE user_id = ?", (u[0],))
    row = cursor.fetchone()
    
    last_s = row[0] if row else None
    if last_s and datetime.fromisoformat(last_s) > datetime.now() - timedelta(hours=4):
        conn.close()
        return await m.answer(f"Ты еще от прошлой кражи не отмылся, шнырь. Жди 4 часа.")

    cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = cursor.fetchone()
    conn.close()

    if not target:
        return await m.answer("Тут некого грабить, ты один на районе как лох.")

    update_u(u[0], last_steal=datetime.now().isoformat())

    if random.random() > 0.6: # 40% шанс украсть
        stolen = round(random.uniform(0.2, 1.2), 2)
        update_u(u[0], size=round(u[2]+stolen, 2))
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.answer(f"🥷 <b>ТЫ КРАСАВА!</b> Подрезал у {target[1]} целых <b>{stolen} см</b>!")
    else:
        fail = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[2]-fail, 2))
        await m.answer(f"🚨 <b>ПОПАЛСЯ!</b> {target[1]} поймал тебя за руку и оторвал <b>{fail} см</b>. Позорище.")

@dp.message(Command("top"))
async def top(m: types.Message):
    log_command()
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT display_name, size FROM users ORDER BY size DESC LIMIT 10")
    except:
        cursor.execute("SELECT username, size FROM users ORDER BY size DESC LIMIT 10")
        
    rows = cursor.fetchall()
    text = "🏆 <b>ТОП ТЕХ, КТО ТЕБЯ ЕБЕТ:</b>\n\n"
    for i, r in enumerate(rows, 1):
        name = r[0] if r[0] else "Какой-то лох"
        text += f"{i}. {name} — <b>{r[1]} см</b>\n"
    await m.answer(text)
    conn.close()

# --- ДОНАТ (ТЕЛЕГРАМ ЗВЕЗДЫ) ---
@dp.message(Command("buy"))
async def buy_stars(m: types.Message):
    log_command()
    await bot.send_invoice(
        chat_id=m.chat.id,
        title="Удлинить огрызок",
        description="Покупка 0.5 см за 15 Telegram Stars. Официальный донат Васе на пиво.",
        payload="buy_05_cm",
        provider_token="", # Для Telegram Stars токен должен быть пустым!
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
    await m.answer(f"🤑 <b>ОПЛАЧЕНО!</b> Твои жалкие Звезды ушли в фонд Васи. Тебе начислено <b>+0.5 см</b>. Будь счастлив, мажор хуев.")

# --- АДМИН ПАНЕЛЬ ДЛЯ @sertof ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer(f"Пошел нахуй отсюда. Ты не @sertof, {random.choice(INSULTS)}.")
    
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
    
    await m.answer(
        "👑 <b>СЛАВА ВЕЛИКОМУ @sertof!</b>\n\n"
        "Слушаюсь и повинуюсь, мой господин.\n\n"
        "📊 <b>СТАТИСТИКА БОТА:</b>\n"
        f"👥 Лохов в базе: <b>{users_count}</b>\n"
        f"🌐 Групп, где мы срем: <b>{chats_count}</b>\n"
        f"⚡ Команд за сегодня: <b>{day_cmds}</b>\n"
        f"📅 Команд за месяц: <b>{month_cmds}</b>\n"
        f"🌍 Команд за год: <b>{year_cmds}</b>\n\n"
        "Твои админские права:\n"
        "Отправить рассылку всем лохам и в чаты: <code>/sendall [текст]</code>\n"
        "<i>Пример: /sendall Здарова пидорасы, сервер уходит на рестарт!</i>"
    )

@dp.message(Command("sendall"))
async def admin_sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer(f"Пшел вон, {random.choice(INSULTS)}, это кнопка для бати.")
    
    text = m.text.replace("/sendall", "").strip()
    if not text:
        return await m.answer("Бля, батя, текст забыл написать.")
    
    users = get_all_users()
    chats = get_all_chats()
    
    targets = list(set(users + chats))
    count = 0
    
    await m.answer(f"Начинаю ебашить ковровую бомбардировку по {len(targets)} целям (ЛС + Группы)...")
    
    for target_id in targets:
        try:
            await bot.send_message(target_id, f"📢 <b>ПОСЛАНИЕ ОТ БАТИ (@sertof):</b>\n\n{text}")
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            pass 
            
    await m.answer(f"✅ Рассылка завершена. Успешно дошло до {count} уебков/чатов.")

# --- РАНДОМНЫЕ НАЕЗДЫ И ОТВЕТЫ В ЧАТАХ ---
@dp.message()
async def auto_insult(m: types.Message):
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    
    text = m.text.lower() if m.text else ""
    
    # Чтобы не дергать АПИ каждый раз, проверяем просто айди бота из токена или слова
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.id
    is_mentioned = "вася" in text or f"@{bot.id}" in text

    if is_reply or is_mentioned:
        return await m.reply(random.choice(MENTION_REPLIES))
    
    if m.chat.type in ['group', 'supergroup'] and random.random() < 0.05: 
        await m.reply(get_claim())
        
    if m.chat.type in ['group', 'supergroup'] and random.random() < 0.01:
        await m.answer(f"Скучно с вами, пидорасы. Кто первым напишет <code>Вася батя</code>, тому накину +1 см.")

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="zadanie", description="Ебаный квест"),
        BotCommand(command="grow", description="Растить хуйню (20ч)"),
        BotCommand(command="status", description="Твоё дно"),
        BotCommand(command="fight", description="Пизделовка"),
        BotCommand(command="casino", description="Казик (1ч)"),
        BotCommand(command="race", description="Гонки (20ч)"),
        BotCommand(command="roulette", description="Рулетка (2ч)"),
        BotCommand(command="steal", description="Спиздить см (4ч)"),
        BotCommand(command="buy", description="Купить см (Звезды)"),
        BotCommand(command="top", description="Топ гигантов"),
        BotCommand(command="info", description="Справка для нытиков")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
