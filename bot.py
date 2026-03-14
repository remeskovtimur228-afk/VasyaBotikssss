import asyncio
import random
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685
SHTEKER_ID = 8349398755
ILISHAK_ID = 6193833286

SHTEKER_FILE = 'shteker_db.txt'
ILISHAK_FILE = 'ilishak_db.txt'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Список ID, которые сейчас находятся под "обстрелом" (Rage Mode)
active_rages = set()

# --- ФУНКЦИИ БАЗЫ ---
def get_random_phrase(filename):
    try:
        if not os.path.exists(filename): return "База пуста!"
        with open(filename, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            return random.choice(lines) if lines else "Админ, заполни базу!"
    except: return "Ошибка БД!"

# --- РЕЖИМ ВЕЛИКОЙ ССОРЫ (RAGE MODE) ---
async def start_rage_mode(chat_id, target_id, filename, target_mention):
    """Минута тотального унижения"""
    if target_id in active_rages: return
    active_rages.add(target_id)
    
    # Количество сообщений за минуту (от 3 до 10)
    burst_count = random.randint(4, 10)
    logging.info(f"Запуск Rage Mode для {target_id}. Сообщений: {burst_count}")

    for _ in range(burst_count):
        await asyncio.sleep(random.randint(5, 12)) # Пауза между выстрелами
        phrase = get_random_phrase(filename)
        # Если это штекер, добавляем его обязательный хештег
        if target_id == SHTEKER_ID and "#АНТИШТЕКЕР" not in phrase:
            phrase += " #АНТИШТЕКЕР"
        
        try:
            # Отправляем сообщение с упоминанием
            await bot.send_message(chat_id, f"Слышь, {target_mention}, ты куда собрался? {phrase}")
        except Exception as e:
            logging.error(f"Ошибка в Rage Mode: {e}")

    active_rages.remove(target_id)

# --- ФОНОВЫЕ НОЧНЫЕ ВБРОСЫ ---
async def random_background_insults(chat_id):
    """Случайные вбросы раз в 1-3 часа"""
    while True:
        await asyncio.sleep(random.randint(3600, 10800)) # 1-3 часа
        target_id = random.choice([SHTEKER_ID, ILISHAK_ID])
        file = SHTEKER_FILE if target_id == SHTEKER_ID else ILISHAK_FILE
        mention = f"ID:{target_id}" # Можно заменить на юзернейм если есть
        
        phrase = get_random_phrase(file)
        try:
            await bot.send_message(chat_id, f"Минутка напоминания: {mention}, ты все еще даун. {phrase}")
        except: pass

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@dp.message()
async def main_handler(message: types.Message):
    if not message.text: return
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.lower()

    # Проверка на упоминание целей (через тег или реплай)
    is_shteker_tagged = (SHTEKER_ID == user_id or 
                         (message.reply_to_message and message.reply_to_message.from_user.id == SHTEKER_ID) or
                         str(SHTEKER_ID) in text or "@" in text) # Упрощенно
    
    is_ilishak_tagged = (ILISHAK_ID == user_id or 
                         (message.reply_to_message and message.reply_to_message.from_user.id == ILISHAK_ID) or
                         str(ILISHAK_ID) in text)

    # 1. Если тегнули ШТЕКЕРА
    if is_shteker_tagged and SHTEKER_ID not in active_rages:
        mention = message.from_user.mention_html() if user_id == SHTEKER_ID else f"это чмо ({SHTEKER_ID})"
        asyncio.create_task(start_rage_mode(chat_id, SHTEKER_ID, SHTEKER_FILE, f"@{message.from_user.username or 'штекер'}"))

    # 2. Если тегнули ИЛИШАКА
    elif is_ilishak_tagged and ILISHAK_ID not in active_rages:
        asyncio.create_task(start_rage_mode(chat_id, ILISHAK_ID, ILISHAK_FILE, f"@{message.from_user.username or 'илишак'}"))

    # 3. Обычный рандомный ответ (1 к 15), если не в режиме ярости
    else:
        if user_id == SHTEKER_ID and random.randint(1, 15) == 1:
            await message.reply(get_random_phrase(SHTEKER_FILE) + " #АНТИШТЕКЕР")
        elif user_id == ILISHAK_ID and random.randint(1, 15) == 1:
            await message.reply(get_random_phrase(ILISHAK_FILE))

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот Вася в режиме 'ВЕЛИКАЯ ССОРА' запущен.")
    # Запускаем фоновые вбросы (нужно будет указать chat_id где они сидят)
    # asyncio.create_task(random_background_insults(CHAT_ID)) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
