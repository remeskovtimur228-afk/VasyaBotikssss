import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Конфигурация
API_TOKEN = '8715185766:AAFa6DQQhdNRuT6uykhX22e3NGa6FgFbkQs'
ADMIN_ID = 8318867685
SHTEKER_ID = 8349398755
ILISHAK_ID = 6193833286

# Состояние бота: 'SHTEKER' или 'ILISHAK'
current_mode = "SHTEKER"

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- БАЗА ДАННЫХ ФРАЗ ---
# В реальности сюда можно добавить тысячи строк
phrases_shteker = [
    "Слышь, штекер, ты опять вылез? Заткнись нахрен. #АНТИШТЕКЕР",
    "Твое мнение тут никого не ебет, штекер недоделанный. #АНТИШТЕКЕР",
    "Админ, уберите этого клоуна, он опять штекер вставил не туда. #АНТИШТЕКЕР",
    "Ты че, реально думаешь, что ты крутой? Ты просто ошибка кода. #АНТИШТЕКЕР",
    # ... добавь сюда еще 1000+ вариантов
]

phrases_ilishak = [
    "Илишак, иди в Бравл Старс тренируйся, рак ебанный.",
    "Ты в ГД даже первый уровень не пройдешь, нулина.",
    "Стандофф не для тебя, иди в кубики играй, даун.",
    "Опять Илишак чет высирает, иди соси в своих мобилках.",
    "Твой скилл в играх — это уровень деменции. Ты не прав во всем.",
    # ... добавь сюда еще 1000+ вариантов
]

generic_insults = [
    "Ты нахуя его тегаешь, даун ебанный?",
    "Слышь, че ты его отмечаешь? Ты такой же дегенерат?",
    "Не трогай говно (его), а то вонять будет, дебил."
]

# --- ЛОГИКА ---

@dp.message_handler(commands=['shteck'])
async def set_shteker(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "SHTEKER"
        await message.answer("Режим переключен на #АНТИШТЕКЕР")

@dp.message_handler(commands=['shick'])
async def set_ilishak(message: types.Message):
    global current_mode
    if message.from_user.id == ADMIN_ID:
        current_mode = "ILISHAK"
        await message.answer("Режим переключен на ИЛИШАК")

@dp.message_handler()
async def main_logic(message: types.Message):
    user_id = message.from_user.id

    # 1. Реакция на упоминание/ответ другими людьми
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in [SHTEKER_ID, ILISHAK_ID]:
            await message.reply(random.choice(generic_insults))
            return

    # 2. Режим АНТИШТЕКЕР
    if current_mode == "SHTEKER":
        if user_id == SHTEKER_ID:
            # Шанс ответа 1 к 10-18 (примерно 7%)
            if random.randint(1, 15) == 1 or "#штекер" in message.text.lower():
                await message.reply(random.choice(phrases_shteker))

    # 3. Режим ИЛИШАК
    elif current_mode == "ILISHAK":
        if user_id == ILISHAK_ID:
            # Рандомная реакция
            if random.randint(1, 15) == 1:
                await message.reply(random.choice(phrases_ilishak))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
