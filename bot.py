import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# Конфигурация
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685
SHTEKER_ID = 8349398755
ILISHAK_ID = 6193833286

# Глобальное состояние (в идеале хранить в БД, но для RING -1 пойдет и так)
current_mode = "SHTEKER"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ОГРОМНАЯ БАЗА ДАННЫХ ---
SHTEKER_HATE = [
    "Слышь, штекер, ты че тут раскукарекался? Завали хлебало. #АНТИШТЕКЕР",
    "Опять этот штекерный высер... Тебе напомнить, кто ты по жизни? #АНТИШТЕКЕР",
    "Штекер, твое место у параши, а не в этом чате. Понял? #АНТИШТЕКЕР",
    "Ты че, реально думаешь, что твои буквы кто-то читает? Даун. #АНТИШТЕКЕР",
    "Админ, кикните эту штекерную макаку, она воняет. #АНТИШТЕКЕР",
    "Штекер, иди в розетку засунься, может хоть так поумнеешь. #АНТИШТЕКЕР",
    "Твое лицо — это ходячий анти-пиар контрацепции. #АНТИШТЕКЕР",
    "Ты — биологический мусор, штекер недоделанный. #АНТИШТЕКЕР"
]

ILISHAK_HATE = [
    "Илишак, ты в ГД даже 'Stereo Madness' не пройдешь, рачина ебанная.",
    "В Стандофф 2 ты просто ходячий фраг для нубов. Удали игру, не позорься.",
    "Твой скилл в Бравле — это уровень моей бабушки после инсульта.",
    "Илишак, ты зачем телефон взял? Иди в песочницу, дегенерат.",
    "Слышь, Илишак, ты тупой как пробка. Твой максимум — это кликеры для даунов.",
    "Да ты в Стандоффе даже в небо попасть не можешь, криворукое чудовище.",
    "Илишак — это диагноз. Сходи к врачу, может лишнюю хромосому удалят.",
    "Твой IQ меньше, чем количество кубков у меня в Бравле на первом аккаунте."
]

GENERIC_HATE = [
    "Слышь, даун ебанный, ты нахуя его тегаешь?",
    "Ты че, его фанатка? Не отмечай это говно здесь.",
    "Зачем ты это чмо тегаешь? Тебе напомнить, что ты тоже дебил?",
    "Еще раз его отметишь — и ты пойдешь нахуй вместе с ним."
]

# --- КОМАНДЫ АДМИНА ---
@dp.message(Command("shteck"))
async def set_shteker(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "SHTEKER"
        await message.answer("✅ Режим переключен на #АНТИШТЕКЕР. Начинаем травить штекера.")

@dp.message(Command("shick"))
async def set_ilishak(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "ILISHAK"
        await message.answer("✅ Режим переключен на ИЛИШАК. Гнобим за ГД и Стандофф.")

# --- ОСНОВНАЯ ЛОГИКА ---
@dp.message()
async def hater_logic(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower() if message.text else ""

    # 1. Если кто-то тегает или отвечает этим двоим
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user.id
        if replied_user in [SHTEKER_ID, ILISHAK_ID]:
            await message.reply(random.choice(GENERIC_HATE))
            return

    # 2. Логика для Штекера
    if current_mode == "SHTEKER" and user_id == SHTEKER_ID:
        # Обязательный ответ на хештег или рандом 1 к 12
        if "#штекер" in text or random.randint(1, 15) == 1:
            await message.reply(random.choice(SHTEKER_HATE))

    # 3. Логика для Илишака
    elif current_mode == "ILISHAK" and user_id == ILISHAK_ID:
        # Рандомная реакция 1 к 12 на любое сообщение
        if random.randint(1, 15) == 1:
            await message.reply(random.choice(ILISHAK_HATE))

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
