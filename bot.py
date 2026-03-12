import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery
from aiogram.utils.payload import decode_payload

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
    
    # Новые колонки для рефералки и прочего
    new_cols = [
        ("last_roulette", "TEXT"),
        ("last_steal", "TEXT"),
        ("display_name", "TEXT"),
        ("referred_by", "INTEGER"), # Кто пригласил
        ("ref_count", "INTEGER DEFAULT 0") # Сколько пригласил
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
        cursor.execute("INSERT INTO users (user_id, username, display_name, size, ref_count) VALUES (?, ?, ?, 0, 0)", (uid, name, display_name))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
    else:
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

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def start(m: types.Message, command: CommandObject):
    log_command()
    uid = m.from_user.id
    
    # Проверяем, есть ли юзер в базе ДО того как создадим
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
    is_new = cursor.fetchone() is None
    conn.close()

    # Создаем/получаем юзера
    u = get_u(uid, m.from_user.full_name, m.from_user.username)

    # Логика рефералки
    if is_new and command.args:
        try:
            ref_id = int(command.args)
            if ref_id != uid: # Сам себя не пригласишь, умник
                referrer = get_u(ref_id, "Unknown")
                # Начисляем бонус пригласившему (+2 см за лоха)
                new_ref_count = (referrer[13] if len(referrer) > 13 else 0) + 1 # ref_count
                update_u(ref_id, size=round(referrer[2] + 2.0, 2), ref_count=new_ref_count)
                update_u(uid, referred_by=ref_id)
                
                try:
                    await bot.send_message(ref_id, f"📈 <b>+2.0 см!</b> Твой реферал @{m.from_user.username or uid} зашел в игру. Соси, мажор!")
                except:
                    pass
        except ValueError:
            pass

    await m.answer(
        f"Здорово, {random.choice(INSULTS)}! Я Вася. \n\n"
        f"⚠️ <b>ВАЖНО:</b> Всё, что я тут несу — это <b>ЮМОР</b>. Я не хочу тебя обидеть.\n\n"
        f"Меня состряпал @sertof. Будем мериться хуями или ты сразу нахуй пойдешь?"
    )

@dp.message(Command("ref"))
async def ref_cmd(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={m.from_user.id}"
    
    # Пытаемся достать ref_count безопасно
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT ref_count FROM users WHERE user_id = ?", (m.from_user.id,))
    cnt = cursor.fetchone()[0] or 0
    conn.close()

    await m.answer(
        f"🤝 <b>ПАРТНЕРКА ДЛЯ КРЫС:</b>\n\n"
        f"Твоя ссылка: <code>{ref_link}</code>\n\n"
        f"За каждого приведенного дегенерата получишь <b>+2.0 см</b> сразу.\n"
        f"Приглашено лохов: <b>{cnt}</b>"
    )

@dp.message(Command("help"))
async def help_cmd(m: types.Message):
    log_command()
    await m.answer(
        "<b>ЧИТАЙ, ПОКА Я ТЕБЕ ЕБАЛО НЕ ВСКРЫЛ:</b>\n\n"
        "<u>/zadanie</u> — Ебанутый квест (раз в день)\n"
        "<u>/grow</u> — Попытка вырасти (20ч кулдаун)\n"
        "<u>/status</u> — Твоя дырявая статистика\n"
        "<u>/ref</u> — Реферальная ссылка (бонус +2см)\n"
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
        "Слушай сюда, кусок дегенерата. Этот бот создан <b>ИСКЛЮЧИТЕЛЬНО</b> ради черного юмора.\n"
        "Вся агрессия, маты и хуеплетство — это образ Васи, ебаного социопата.\n\n"
        "🛑 <b>ВАЖНЫЕ ПРАВИЛА:</b>\n"
        "1. Пизделовка (/fight) — шанс выиграть мизерный. Страдай.\n"
        "2. Задания (/zadanie) — это просто тупой рофл.\n"
        "3. Вася не управляет группами, он просто срет в чат.\n\n"
        "Создатель: @sertof. Жаловаться маме."
    )

@dp.message(Command("zadanie"))
async def zadanie(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    now = str(datetime.now().date())
    if u[5] == now:
        await m.answer(f"Хули ты ноешь, {random.choice(INSULTS)}? Твоё задание: <i>{u[6]}</i>. Иди делай!")
    else:
        t = get_task()
        update_u(m.from_user.id, last_task=now, current_task=t)
        await m.answer(f"Слушай сюда, {random.choice(INSULTS)}. Твой квест:\n\n🔥 {t}")

@dp.message(Command("grow"))
async def grow(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[3] and datetime.fromisoformat(u[3]) > datetime.now() - timedelta(hours=20):
        await m.answer(f"Куда лезешь, {random.choice(INSULTS)}?! Жди 20 часов.")
        return
    
    change = round(random.uniform(-1.0, 1.2), 2)
    new_s = round(u[2] + change, 2) 
    update_u(m.from_user.id, size=new_s, last_grow=datetime.now().isoformat())
    
    if change > 0:
        await m.answer(f"Опа, {random.choice(INSULTS)}. Подрос на <b>{change} см</b>. Теперь: <u>{new_s} см</u>.")
    else:
        await m.answer(f"ХА-ХА-ХА! Ушел внутрь на <b>{abs(change)} см</b>. Итого: <u>{new_s} см</u>.")

@dp.message(Command("status"))
async def status(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    s = u[2]
    r = "Бог ебли" if s > 30 else "Норм хуй" if s > 15 else "Огрызок" if s > 0 else "ОТРИЦАТЕЛЬНЫЙ ПИДОРАС"
    disp = m.from_user.username if m.from_user.username else m.from_user.full_name
    await m.answer(f"📊 <b>ТВОЁ ДОСЬЕ ({disp}):</b>\n\n"
                   f"Длина: <i>{s} см</i>\n"
                   f"Ранг: <u>{r}</u>\n"
                   f"Ты по жизни: <i>{random.choice(INSULTS)}</i>")

@dp.message(Command("fight"))
async def fight(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if random.random() > 0.95: 
        win = round(random.uniform(1.0, 3.5), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.answer(f"🤜 <b>ПИЗДЕЦ НЕМЫСЛИМЫЙ!</b> Вырубил быка. Лови <b>+{win} см</b>.")
    else:
        loss = round(random.uniform(0.6, 2.5), 2)
        update_u(u[0], size=round(u[2]-loss, 2)) 
        await m.answer(f"💀 <b>ФИАСКО!</b> Минус <b>{loss} см</b>.")

@dp.message(Command("race"))
async def race(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[7] and datetime.fromisoformat(u[7]) > datetime.now() - timedelta(hours=20):
        await m.answer(f"Твоя колымага еще на свалке. Жди 20 часов.")
        return

    await m.answer("🏎 <b>Заезд пошел... Моча летит из окон...</b>")
    await asyncio.sleep(2)
    if random.random() > 0.6:
        update_u(u[0], size=round(u[2]+0.7, 2), last_race=datetime.now().isoformat())
        await m.answer(f"🏁 Первое место! +0.7 см.")
    else:
        update_u(u[0], size=round(u[2]-1.0, 2), last_race=datetime.now().isoformat())
        await m.answer(f"💩 Ты врезался в фуру с навозом. -1.0 см.")

@dp.message(Command("casino"))
async def casino(m: types.Message):
    log_command()
    u = get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    if u[8] and datetime.fromisoformat(u[8]) > datetime.now() - timedelta(hours=1):
        diff = datetime.fromisoformat(u[8]) + timedelta(hours=1) - datetime.now()
        minutes = int(diff.total_seconds() // 60)
        await m.answer(f"Казик закрыт. Приходи через {minutes} мин.")
        return

    if random.random() > 0.8:
        update_u(u[0], size=round(u[2]+3.5, 2), last_casino=datetime.now().isoformat())
        await m.answer(f"🎰 <b>СУКА, ПОВЕЗЛО!</b> +3.5 см.")
    else:
        update_u(u[0], size=round(u[2]-2.5, 2), last_casino=datetime.now().isoformat())
        await m.answer(f"🎰 <b>ЗЕРО, ЕБЛАН!</b> -2.5 см.")

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
        await m.answer(f"Ствол перегрелся. Жди 2 часа.")
        return

    await m.answer("🔫 <b>Крутишь барабан...</b>")
    await asyncio.sleep(1.5)
    update_u(u[0], last_roulette=datetime.now().isoformat())
    if random.random() < 0.16: 
        loss = round(random.uniform(2.0, 5.0), 2)
        update_u(u[0], size=round(u[2]-loss, 2))
        await m.answer(f"💥 <b>ВЫСТРЕЛ!</b> Твой хуй отсох на <b>{loss} см</b>.")
    else:
        win = round(random.uniform(0.3, 1.0), 2)
        update_u(u[0], size=round(u[2]+win, 2))
        await m.answer(f"💨 <b>Щелчок...</b> Пронесло. +<b>{win} см</b>.")

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
        return await m.answer(f"Жди 4 часа, шнырь.")

    cursor.execute("SELECT user_id, display_name, size FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u[0],))
    target = cursor.fetchone()
    conn.close()

    if not target:
        return await m.answer("Тут некого грабить.")

    update_u(u[0], last_steal=datetime.now().isoformat())
    if random.random() > 0.6: 
        stolen = round(random.uniform(0.2, 1.2), 2)
        update_u(u[0], size=round(u[2]+stolen, 2))
        update_u(target[0], size=round(target[2]-stolen, 2))
        await m.answer(f"🥷 <b>ТЫ КРАСАВА!</b> Подрезал у {target[1]} целых <b>{stolen} см</b>!")
    else:
        fail = round(random.uniform(0.5, 1.5), 2)
        update_u(u[0], size=round(u[2]-fail, 2))
        await m.answer(f"🚨 <b>ПОПАЛСЯ!</b> {target[1]} оторвал тебе <b>{fail} см</b>.")

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

@dp.message(Command("buy"))
async def buy_stars(m: types.Message):
    log_command()
    await bot.send_invoice(
        chat_id=m.chat.id,
        title="Удлинить огрызок",
        description="Покупка 0.5 см за 15 Telegram Stars.",
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
    await m.answer(f"🤑 <b>ОПЛАЧЕНО!</b> +0.5 см. Будь счастлив, мажор.")

@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer(f"Пошел нахуй отсюда.")
    
    conn = sqlite3.connect('vasya_hell_final.db')
    cursor = conn.cursor()
    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    chats_count = cursor.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    today = str(datetime.now().date())
    day_cmds = cursor.execute("SELECT count FROM command_stats WHERE date = ?", (today,)).fetchone()
    day_cmds = day_cmds[0] if day_cmds else 0
    conn.close()
    
    await m.answer(
        "👑 <b>СЛАВА ВЕЛИКОМУ @sertof!</b>\n\n"
        f"👥 Лохов: <b>{users_count}</b>\n"
        f"🌐 Групп: <b>{chats_count}</b>\n"
        f"⚡ Команд за сегодня: <b>{day_cmds}</b>\n\n"
        "Рассылка: <code>/sendall [текст]</code>"
    )

@dp.message(Command("sendall"))
async def admin_sendall(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer(f"Пшел вон.")
    text = m.text.replace("/sendall", "").strip()
    if not text: return await m.answer("Текст?")
    
    users = get_all_users()
    chats = get_all_chats()
    targets = list(set(users + chats))
    count = 0
    await m.answer(f"Ебашу по {len(targets)} целям...")
    for target_id in targets:
        try:
            await bot.send_message(target_id, f"📢 <b>ПОСЛАНИЕ ОТ БАТИ (@sertof):</b>\n\n{text}")
            count += 1
            await asyncio.sleep(0.05) 
        except: pass 
    await m.answer(f"✅ Дошло до {count} уебков.")

@dp.message()
async def auto_insult(m: types.Message):
    get_u(m.from_user.id, m.from_user.full_name, m.from_user.username)
    text = m.text.lower() if m.text else ""
    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.id
    is_mentioned = "вася" in text

    if is_reply or is_mentioned:
        return await m.reply(random.choice(MENTION_REPLIES))
    
    if m.chat.type in ['group', 'supergroup'] and random.random() < 0.05: 
        await m.reply(get_claim())

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="zadanie", description="Ебаный квест"),
        BotCommand(command="grow", description="Растить (20ч)"),
        BotCommand(command="status", description="Твоё дно"),
        BotCommand(command="ref", description="Пригласить лоха"),
        BotCommand(command="fight", description="Пизделовка"),
        BotCommand(command="casino", description="Казик (1ч)"),
        BotCommand(command="race", description="Гонки (20ч)"),
        BotCommand(command="roulette", description="Рулетка (2ч)"),
        BotCommand(command="steal", description="Спиздить см (4ч)"),
        BotCommand(command="buy", description="Купить см (Звезды)"),
        BotCommand(command="top", description="Топ гигантов"),
        BotCommand(command="info", description="Справка")
    ])
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
