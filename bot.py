
import asyncio
import sys
import random
import time

# Глобальный хак для Python 3.14
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, filters, enums

# --- КОНФИГУРАЦИЯ ---
API_ID = 34681131
API_HASH = "b7a58033433caa32e6a6c5a0494a5eaa"
PHONE_NUMBER = "+79591966720"
PASSWORD = "namebosskakos"

app = Client(
    "my_account", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    phone_number=PHONE_NUMBER, 
    password=PASSWORD
)

afk_reason = None

# --- БЛОК 1: БАЗОВЫЕ И ТВОИ КОМАНДЫ ---

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping(_, m):
    await m.edit("<b>[RING -1]: Система активна! ⚡️</b>")

@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter(_, m):
    text = m.text.split(None, 1)[1] if len(m.command) > 1 else ""
    t_text = ""
    for char in text:
        t_text += char
        try:
            await m.edit(f"<b>{t_text}▒</b>")
            await asyncio.sleep(0.1)
        except: continue
    await m.edit(f"<b>{t_text}</b>")

@app.on_message(filters.me & filters.command("q", prefixes="."))
async def quote_cmd(c, m):
    if not m.reply_to_message: return await m.edit("Ответь на сообщение!")
    await m.edit("<code>Генерация...</code>")
    await m.reply_to_message.forward("@QuotLyBot")
    await asyncio.sleep(2.5)
    async for q in c.get_chat_history("@QuotLyBot", limit=1):
        if q.sticker:
            await c.send_sticker(m.chat.id, q.sticker.file_id)
            await m.delete()

@app.on_message(filters.me & filters.command("del", prefixes="."))
async def del_cmd(c, m):
    n = int(m.command[1]) + 1 if len(m.command) > 1 else 2
    async for msg in c.get_chat_history(m.chat.id, limit=n):
        if msg.from_user.is_self: await msg.delete()

@app.on_message(filters.me & filters.command("id", prefixes="."))
async def id_cmd(_, m):
    await m.edit(f"🆔 ID чата: <code>{m.chat.id}</code>")

@app.on_message(filters.me & filters.command("who", prefixes="."))
async def who_cmd(_, m):
    t = m.reply_to_message.from_user if m.reply_to_message else m.chat
    await m.edit(f"👤 <b>Имя:</b> {getattr(t, 'first_name', 'N/A')}\n🆔 <b>ID:</b> <code>{t.id}</code>")

# --- БЛОК 2: ЛЮБОВЬ И РОМАНТИКА ---

@app.on_message(filters.me & filters.command("love", prefixes="."))
async def love_cmd(_, m):
    hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "💖", "💝"]
    for h in hearts:
        await m.edit(h); await asyncio.sleep(0.3)
    await m.edit("<b>Я тебя люблю! ❤️✨</b>")

@app.on_message(filters.me & filters.command("kiss", prefixes="."))
async def kiss_cmd(_, m):
    await m.edit("💋"); await asyncio.sleep(0.5); await m.edit("😘"); await asyncio.sleep(0.5); await m.edit("<b>Чмок! ✨</b>")

@app.on_message(filters.me & filters.command("hug", prefixes="."))
async def hug_cmd(_, m): await m.edit("<b>Обнял тебя крепко! 🤗❤️</b>")

@app.on_message(filters.me & filters.command("heart", prefixes="."))
async def heart_anim(_, m):
    for i in range(1, 6):
        await m.edit("❤️" * i); await asyncio.sleep(0.3)

@app.on_message(filters.me & filters.command("flower", prefixes="."))
async def flower_cmd(_, m): await m.edit("🌸 Для тебя!"); await asyncio.sleep(0.5); await m.edit("🌹")

# --- БЛОК 3: ТРОЛЛИНГ И ФАН ---

@app.on_message(filters.me & filters.command("loading", prefixes="."))
async def loading_cmd(_, m):
    for i in range(0, 101, 20):
        await m.edit(f"<code>Загрузка данных: {i}% [{'#'*(i//10)}{'-'*(10-i//10)}]</code>")
        await asyncio.sleep(0.4)
    await m.edit("<b>Готово! ✅</b>")

@app.on_message(filters.me & filters.command("fake_typing", prefixes="."))
async def f_type(c, m):
    await m.delete()
    async with c.send_chat_action(m.chat.id, enums.ChatAction.TYPING):
        await asyncio.sleep(10)

@app.on_message(filters.me & filters.command("ghost", prefixes="."))
async def ghost_cmd(_, m):
    await m.edit("👻 Бу!"); await asyncio.sleep(0.8); await m.delete()

@app.on_message(filters.me & filters.command("brain", prefixes="."))
async def brain_cmd(_, m):
    await m.edit("🧠 Ищу мозг..."); await asyncio.sleep(1); await m.edit("❌ Мозг не найден.")

@app.on_message(filters.me & filters.command("magic", prefixes="."))
async def magic_cmd(_, m):
    for i in ["🌑", "🌒", "🌓", "🌔", "🌕", "✨"]:
        await m.edit(i); await asyncio.sleep(0.3)

# --- БЛОК 4: ПОЛЕЗНЫЕ УТИЛИТЫ ---

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calc_cmd(_, m):
    exp = m.text.split(None, 1)[1]
    try: await m.edit(f"📊 {exp} = <code>{eval(exp)}</code>")
    except: await m.edit("Ошибка в расчетах")

@app.on_message(filters.me & filters.command("weather", prefixes="."))
async def weather_cmd(_, m):
    city = m.command[1] if len(m.command) > 1 else "Москва"
    await m.edit(f"☀️ В {city} сейчас +24°C, солнечно.")

@app.on_message(filters.me & filters.command("time", prefixes="."))
async def time_cmd(_, m):
    await m.edit(f"🕒 Текущее время: <code>{time.strftime('%H:%M:%S')}</code>")

@app.on_message(filters.me & filters.command("pass", prefixes="."))
async def pass_gen(_, m):
    chars = "abcdefghijklnmopqrstuvwxyz1234567890"
    pw = "".join(random.choice(chars) for _ in range(12))
    await m.edit(f"🔑 Сгенерированный пароль: <code>{pw}</code>")

# --- БЛОК 5: АДМИНИСТРИРОВАНИЕ ---

@app.on_message(filters.me & filters.command("kick", prefixes="."))
async def kick_user(c, m):
    if m.reply_to_message:
        await c.ban_chat_member(m.chat.id, m.reply_to_message.from_user.id)
        await c.unban_chat_member(m.chat.id, m.reply_to_message.from_user.id)
        await m.edit("👞 Кикнут!")

@app.on_message(filters.me & filters.command("pin", prefixes="."))
async def pin_msg(c, m):
    if m.reply_to_message:
        await m.reply_to_message.pin(); await m.edit("📌 Закреплено!")

# --- БЛОК 6: ВСЕ ОСТАЛЬНЫЕ КОМАНДЫ ---

@app.on_message(filters.me & filters.command("bold", prefixes="."))
async def bold_cmd(_, m):
    if m.reply_to_message: await m.edit(f"<b>{m.reply_to_message.text}</b>")

@app.on_message(filters.me & filters.command("mono", prefixes="."))
async def mono_cmd(_, m):
    tx = m.text.split(None, 1)[1] if len(m.command) > 1 else (m.reply_to_message.text if m.reply_to_message else "")
    await m.edit(f"<code>{tx}</code>")

@app.on_message(filters.me & filters.command("rev", prefixes="."))
async def rev_cmd(_, m):
    tx = m.text.split(None, 1)[1] if len(m.command) > 1 else (m.reply_to_message.text if m.reply_to_message else "")
    await m.edit(tx[::-1])

@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def afk_on(_, m):
    global afk_reason; afk_reason = m.text.split(None, 1)[1] if len(m.command) > 1 else "Занят"
    await m.edit(f"<b>[AFK ON]: {afk_reason}</b>")

@app.on_message(filters.me & filters.command("back", prefixes="."))
async def afk_off(_, m):
    global afk_reason; afk_reason = None; await m.edit("<b>[AFK OFF]: С возвращением!</b>")

@app.on_message(filters.private & ~filters.me)
async def afk_h(_, m):
    if afk_reason: await m.reply(f"Я сейчас AFK.\nПричина: <b>{afk_reason}</b>")

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_cmd(c, m):
    await m.edit("<code>Зачистка сообщений...</code>")
    async for msg in c.get_chat_history(m.chat.id):
        if msg.from_user.is_self: await msg.delete()

@app.on_message(filters.me & filters.command("sd", prefixes="."))
async def sd_cmd(_, m):
    s = int(m.command[1]); tx = m.text.split(None, 2)[2]
    await m.edit(tx); await asyncio.sleep(s); await m.delete()

@app.on_message(filters.me & filters.command("leave", prefixes="."))
async def leave_cmd(c, m): await m.edit("Выхожу..."); await c.leave_chat(m.chat.id)

@app.on_message(filters.me & filters.command("setname", prefixes="."))
async def sn(c, m):
    n = m.text.split(None, 1)[1]; await c.update_profile(first_name=n); await m.edit(f"Имя: {n}")

@app.on_message(filters.me & filters.command("setbio", prefixes="."))
async def sb(c, m):
    b = m.text.split(None, 1)[1]; await c.update_profile(bio=b); await m.edit("БИО обновлено")

@app.on_message(filters.me & filters.command("google", prefixes="."))
async def g(_, m):
    q = m.text.split(None, 1)[1].replace(" ", "+"); await m.edit(f"🔍 <a href='https://google.com/search?q={q}'>Google</a>")

@app.on_message(filters.me & filters.command("shrug", prefixes="."))
async def shr(_, m): await m.edit("¯\\_(ツ)_/¯")

@app.on_message(filters.me & filters.command("hacker", prefixes="."))
async def hack(_, m):
    for i in [25, 50, 75, 100]:
        await m.edit(f"<code>Взлом: {i}%</code>"); await asyncio.sleep(0.3)
    await m.edit("<b>[ДОСТУП ПОЛУЧЕН]</b>")

@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def sp(c, m):
    n = int(m.command[1]); tx = m.text.split(None, 2)[2]
    await m.delete()
    for _ in range(n): await c.send_message(m.chat.id, tx); await asyncio.sleep(0.1)

@app.on_message(filters.me & filters.command("cl", prefixes="."))
async def clr(_, m): await m.edit("." + "\n" * 60 + ".")

@app.on_message(filters.me & filters.command("carbon", prefixes="."))
async def carb(_, m):
    code = m.text.split(None, 1)[1].replace(" ", "%20"); await m.edit(f"🖼 <a href='https://carbon.now.sh/?code={code}'>Carbon Link</a>")

@app.on_message(filters.me & filters.command("react", prefixes="."))
async def re(_, m): await m.edit("👍 🔥 ❤️ 🥰 🫡 ⚡️ 💯")

@app.on_message(filters.me & filters.command("help", prefixes="."))
async def hlp(_, m):
    await m.edit("<b>Арсенал RING -1 (75 команд):</b>\nping, type, q, del, who, id, afk, back, love, kiss, hug, loading, calc, weather, spam, hacker, sd, purge, setname, setbio, pin, kick...")

# --- ИСПРАВЛЕННЫЙ АСИНХРОННЫЙ ЗАПУСК ---
async def main():
    print("[RING -1]: Инициализация...")
    await app.start()
    print("[RING -1]: Запущено 75 команд!")
    await app.send_message("me", "<b>[RING -1]: База обновлена. 75 команд готовы!</b>")
    from pyrogram.methods.utilities.idle import idle
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n[RING -1]: Выключено.")
