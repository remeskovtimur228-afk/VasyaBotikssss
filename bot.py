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

# Файлы базы данных
SHTEKER_FILE = 'shteker_db.txt'
ILISHAK_FILE = 'ilishak_db.txt'

# Состояние (по умолчанию Штекер)
current_mode = "SHTEKER"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- РАБОТА С ГИГАНТСКОЙ БАЗОЙ ---
def check_and_create_db():
    """Создает файлы базы с начальным паком, если их нет"""
    if not os.path.exists(SHTEKER_FILE):
        with open(SHTEKER_FILE, 'w', encoding='utf-8') as f:
            # Сюда можно вписать хоть 1000 строк сразу
            f.write("Слышь, штекер, завали ебало. #АНТИШТЕКЕР\n")
            f.write("Штекер, ты че, опять из палаты сбежал? #АНТИШТЕКЕР\n")
            f.write("Твое мнение весит меньше, чем твои мозги, штекер. #АНТИШТЕКЕР\n")
            f.write("Админ, уберите это штекерное недоразумение. #АНТИШТЕКЕР\n")

    if not os.path.exists(ILISHAK_FILE):
        with open(ILISHAK_FILE, 'w', encoding='utf-8') as f:
            f.write("Илишак, ты в ГД даже прыгать не умеешь, рак.\n")
            f.write("Стандофф 2 — не твое, иди в кубики играй, даун.\n")
            f.write("Твой скилл в Бравле — это уровень дна океана.\n")
            f.write("Илишак, ты тупой как пробка, удали все игры.\n")

def get_random_phrase(filename):
    """Выбирает рандомную фразу из файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            return random.choice(lines) if lines else "База пуста, админ, заполни файл!"
    except Exception:
        return "Ошибка чтения базы!"

# --- КОМАНДЫ АДМИНА ---
@dp.message(Command("shteck"))
async def cmd_shteck(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "SHTEKER"
        await message.answer("🦾 Режим #АНТИШТЕКЕР активирован. Смерть штекеру.")

@dp.message(Command("shick"))
async def cmd_shick(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "ILISHAK"
        await message.answer("🎮 Режим ИЛИШАК активирован. Гнобим за ГД и Стандофф.")

# --- ЛОГИКА АГРА ---
@dp.message()
async def hater_handler(message: types.Message):
    if not message.text: return
    user_id = message.from_user.id
    text_lower = message.text.lower()

    # 1. Реакция на тех, кто тегает цель
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id
        if target in [SHTEKER_ID, ILISHAK_ID]:
            await message.reply("Ты нахуя это чмо тегаешь, даун ебанный?")
            return

    # 2. Логика режима АНТИШТЕКЕР
    if current_mode == "SHTEKER" and user_id == SHTEKER_ID:
        # Обязательно на тег или раз в 10-18 сообщений
        if "#штекер" in text_lower or random.randint(1, 14) == 1:
            phrase = get_random_phrase(SHTEKER_FILE)
            await message.reply(phrase)

    # 3. Логика режима ИЛИШАК
    elif current_mode == "ILISHAK" and user_id == ILISHAK_ID:
        # Раз в 10-18 сообщений
        if random.randint(1, 14) == 1:
            phrase = get_random_phrase(ILISHAK_FILE)
            await message.reply(phrase)

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    check_and_create_db() # Инициализируем файлы
    print("Бот Вася запущен и готов бесить людей.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка: {e}")
