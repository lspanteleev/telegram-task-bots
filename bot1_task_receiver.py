"""
BOT 1: Task Receiver
Receives task requests for website page development
"""
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from database import add_task
from config import BOT1_TOKEN

logger = logging.getLogger(__name__)

# States for conversation
class TaskForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()

async def setup_bot1(dp: Dispatcher, bot: Bot):
    """Setup Bot 1 handlers"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📝 Новая задача")]],
            resize_keyboard=True
        )
        await message.answer(
            "🤖 Привет! Я бот для приёма задач на разработку страниц.\n"
            "Нажми кнопку или используй /new_task",
            reply_markup=kb
        )
    
    @dp.message(F.text == "📝 Новая задача")
    @dp.message(Command("new_task"))
    async def new_task(message: types.Message, state: FSMContext):
        await state.set_state(TaskForm.waiting_for_title)
        await message.answer("📌 Напиши название задачи:")
    
    @dp.message(TaskForm.waiting_for_title)
    async def process_title(message: types.Message, state: FSMContext):
        await state.update_data(title=message.text)
        await state.set_state(TaskForm.waiting_for_description)
        await message.answer("📝 Напиши описание задачи:")
    
    @dp.message(TaskForm.waiting_for_description)
    async def process_description(message: types.Message, state: FSMContext):
        await state.update_data(description=message.text)
        await state.set_state(TaskForm.waiting_for_priority)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔴 Высокий"), KeyboardButton(text="🟡 Средний")],
                [KeyboardButton(text="🟢 Низкий")]
            ],
            resize_keyboard=True
        )
        await message.answer("⚡ Выбери приоритет:", reply_markup=kb)
    
    @dp.message(TaskForm.waiting_for_priority)
    async def process_priority(message: types.Message, state: FSMContext):
        priority_map = {
            "🔴 Высокий": "high",
            "🟡 Средний": "medium",
            "🟢 Низкий": "low"
        }
        priority = priority_map.get(message.text, "medium")
        
        data = await state.get_data()
        task_id = add_task(
            title=data["title"],
            description=data["description"],
            priority=priority
        )
        
        await state.clear()
        await message.answer(
            f"✅ Задача #{task_id} добавлена в очередь!\n"
            f"Название: {data['title']}\n"
            f"Приоритет: {message.text}"
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "📖 Доступные команды:\n"
            "/start - главное меню\n"
            "/new_task - создать задачу\n"
            "/help - помощь"
        )
