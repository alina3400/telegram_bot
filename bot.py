import asyncio
import json
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = '8367203167:AAGsmftYaiBOMSlbxoJCd6MqbjeCwR8hRD8'
ADMIN_ID = 1992938767

# Клавиатура главного меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="FAQ")],
        [KeyboardButton(text="Опрос")],
        [KeyboardButton(text="Связаться с оператором")]
    ],
    resize_keyboard=True
)

class OprosStates(StatesGroup):
    name = State()
    phone = State()
    time = State()
    email = State()

FAQ_DATA = {
    "Как начать работу с ботом?": "Нажмите кнопку Опрос и заполните анкету.",
    "Где найти туториалы?": "Туториалы можно найти на нашем канале.",
    "Есть ли группа в ВК?": "Да, ссылка (vk.com/marvelous_designer_news)",
    "Есть ли гарантия?": "Да, мы предоставляем гарантию на все наши услуги."
}

OPROS_FILE = "opros.json"
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_opros(data):
    oproses = []
    if os.path.exists(OPROS_FILE):
        with open(OPROS_FILE, 'r', encoding='utf-8') as f:
            try:
                oproses = json.load(f)
            except:
                oproses = []
    oproses.append(data)
    with open(OPROS_FILE, 'w', encoding='utf-8') as f:
        json.dump(oproses, f, ensure_ascii=False, indent=2)

def validate_phone(phone):
    pattern = r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}$'
    return re.match(pattern, phone) is not None

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

async def notify_admin(bot, opros_data):
    message = (
        f"Новая заявка\n"
        f"Имя: {opros_data['name']}\n"
        f"Телефон: {opros_data['phone']}\n"
        f"Время связи: {opros_data['time']}\n"
        f"Email: {opros_data['email']}\n"
        f"Пользователь: @{opros_data['username'] or opros_data['user_id']}\n"
        f"Время: {opros_data['timestamp']}"
    )
    await bot.send_message(ADMIN_ID, message)

async def start(message: types.Message):
    user_id = str(message.from_user.id)
    history = load_history()
    if user_id not in history:
        history[user_id] = []
    
    history[user_id].append({
        "action": "start",
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    
    await message.answer(
        f"Здравствуйте!\n\n"
        f"Я бот для сбора заявок. Выберите действие в меню.",
        reply_markup=main_keyboard
    )

async def faq_handler(message: types.Message):
    faq_text = "Частые вопросы:\n\n"
    for i, (q, a) in enumerate(FAQ_DATA.items(), 1):
        faq_text += f"{i}. {q}\n   {a}\n\n"
    
    await message.answer(faq_text, reply_markup=main_keyboard)

async def start_opros(message: types.Message, state: FSMContext):
    await message.answer(
        "Опрос\n\n"
        "Пожалуйста, ответьте на несколько вопросов.\n\n"
        "Как вас зовут?",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(OprosStates.name)

async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("Пожалуйста, введите ваше имя (минимум 2 символа):")
        return
    
    await state.update_data(name=message.text)
    await message.answer(
        "Введите ваш номер телефона:\n"
        "Формат: +7XXXXXXXXXX или 8XXXXXXXXXX"
    )
    await state.set_state(OprosStates.phone)

async def process_phone(message: types.Message, state: FSMContext):
    if not validate_phone(message.text):
        await message.answer(
            "Неверный формат телефона. Пожалуйста, введите номер в формате:\n"
            "+7XXXXXXXXXX или 8XXXXXXXXXX"
        )
        return
    
    await state.update_data(phone=message.text)
    await message.answer(
        "Укажите удобное время для связи:\n"
        "(например: будни 10:00-18:00)"
    )
    await state.set_state(OprosStates.time)

async def process_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer(
        "Введите ваш email для получения информации:"
    )
    await state.set_state(OprosStates.email)

async def process_email(message: types.Message, state: FSMContext, bot: Bot):
    if not validate_email(message.text):
        await message.answer(
            "Неверный формат email. Пожалуйста, введите email в формате:\n"
            "example@mail.ru"
        )
        return
    
    data = await state.get_data()
    
    opros_data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "name": data['name'],
        "phone": data['phone'],
        "time": data['time'],
        "email": message.text,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_opros(opros_data)
    
    try:
        await notify_admin(bot, opros_data)
    except Exception as e:
        print(f"Admin notification failed: {e}")
    
    await message.answer(
        "Спасибо за участие в опросе!\n\n"
        "Ваши ответы сохранены.",
        reply_markup=main_keyboard
    )
    
    await state.clear()

async def contact_operator(message: types.Message, bot: Bot):
    user_name = message.from_user.first_name or message.from_user.username
    
    await message.answer(
        "Связь с оператором\n\n"
        "Ваша заявка передана оператору.",
        reply_markup=main_keyboard
    )
    
    operator_msg = (
        f"Заявка на связь\n"
        f"Пользователь: {user_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'нет'}\n"
        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await bot.send_message(ADMIN_ID, operator_msg)

async def help_handler(message: types.Message):
    await message.answer(
        "Помощь\n\n"
        "Кнопки меню:\n"
        "FAQ - ответы на вопросы\n"
        "Опрос - заполнить анкету\n"
        "Связаться с оператором - запрос на связь\n\n"
        "Команды:\n"
        "/start - главное меню\n"
        "/help - эта справка",
        reply_markup=main_keyboard
    )

async def show_oproses(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды")
        return
    
    if not os.path.exists(OPROS_FILE):
        await message.answer("Нет сохраненных заявок")
        return
    
    with open(OPROS_FILE, 'r', encoding='utf-8') as f:
        opros = json.load(f)
    
    if not opros:
        await message.answer("Нет сохраненных заявок")
        return
    
    for opros in opros[-5:]:
        text = (
            f"Заявка #{opros['id']}\n"
            f"Имя: {opros['name']}\n"
            f"Телефон: {opros['phone']}\n"
            f"Время связи: {opros['time']}\n"
            f"Email: {opros['email']}\n"
            f"Пользователь: @{opros['username'] or opros['user_id']}\n"
            f"Время: {opros['timestamp']}"
        )
        await message.answer(text)

async def main():
    storage = MemoryStorage()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)
    
    dp.message.register(start, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(show_oproses, Command("opros"))
    
    dp.message.register(faq_handler, lambda m: m.text == "FAQ")
    dp.message.register(start_opros, lambda m: m.text == "Опрос")
    dp.message.register(contact_operator, lambda m: m.text == "Связаться с оператором")
    
    dp.message.register(process_name, OprosStates.name)
    dp.message.register(process_phone, OprosStates.phone)
    dp.message.register(process_time, OprosStates.time)
    dp.message.register(process_email, OprosStates.email)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())