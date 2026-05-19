"""
Main entry point for both Telegram bots
Bot 1: Task Receiver
Bot 2: Task Tracker
"""
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT1_TOKEN, BOT2_TOKEN, TASK_RECEIVER_CHAT_ID, MTPROTO_PROXY
from database import (
    init_db, add_task, get_all_tasks, get_task_by_id, 
    update_task_status, get_tasks_by_status, assign_task, get_user_tasks,
    calculate_priority
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Auto-detected admin (first user to use /manage becomes admin)
ADMIN_USER_ID = None

# States for Bot 1
class TaskForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
    waiting_for_tz_url = State()

# Status mapping
STATUSES = {
    "new": "🆕 Новая",
    "in_progress": "⏳ В работе",
    "review": "👀 На проверке",
    "done": "✅ Готово",
    "cancelled": "❌ Отменено"
}

STATUS_ORDER = ["new", "in_progress", "review", "done", "cancelled"]

# ============ BOT 1: TASK RECEIVER ============

# ============ BOT 1: TASK RECEIVER ============

def register_bot1_handlers(dp: Dispatcher):
    """Register Bot 1 handlers"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📝 Новая задача")], [KeyboardButton(text="📊 Мои задачи")]],
            resize_keyboard=True
        )
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Я бот для приёма и отслеживания задач на разработку веб-страниц.\n\n"
            "Что я могу:\n"
            "📝 Создавать новые задачи\n"
            "📊 Показывать статус твоих задач\n"
            "🔔 Уведомлять об изменениях\n\n"
            "Команды:\n"
            "/new_task - создать задачу\n"
            "/mystatus - посмотреть твои задачи\n"
            "/help - справка\n\n"
            "Выбери действие ниже 👇",
            reply_markup=kb
        )
    
    @dp.message(F.text == "📊 Мои задачи")
    @dp.message(Command("mystatus"))
    async def cmd_mystatus(message: types.Message):
        """Show user's own tasks"""
        tasks = get_user_tasks(message.from_user.id)
        
        if not tasks:
            await message.answer("📭 У тебя нет созданных задач")
            return
        
        text = "📋 Твои задачи:\n\n"
        for task in tasks:
            assigned = f" → @{task.get('assigned_username')}" if task.get('assigned_to') else " (не назначена)"
            text += f"#{task['id']} - {task['title']}\n"
            text += f"Статус: {STATUSES.get(task['status'], task['status'])}\n"
            text += f"Дата запуска: {task.get('deadline', 'не указана')}\n"
            text += f"Назначена: {assigned}\n\n"
        
        await message.answer(text)
    
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
        await state.set_state(TaskForm.waiting_for_deadline)
        await message.answer(
            "📅 Укажи дату запуска проекта в формате ДД.ММ.ГГГГ\n"
            "Например: 25.05.2026\n\n"
        )
    
    @dp.message(TaskForm.waiting_for_deadline)
    async def process_deadline(message: types.Message, state: FSMContext):
        # Parse date from DD.MM.YYYY format
        try:
            date_obj = datetime.strptime(message.text, "%d.%m.%Y")
            deadline_str = date_obj.strftime("%Y-%m-%d")
            await state.update_data(deadline=deadline_str)
        except ValueError:
            await message.answer("❌ Неправильный формат! Используй ДД.ММ.ГГГГ (например: 25.05.2026)")
            return
        
        await state.set_state(TaskForm.waiting_for_tz_url)
        await message.answer(
            "🔗 Отправь ссылку на описание ТЗ\n\n"
            "Обязательно изучите пример и руководствуйтесь им при составлении описания:\n"
            "https://docs.google.com/document/d/1leQSF_SDwyXj2xYeJXxVDDv9Yhpku8YEQFkcOBcVYxw/edit?usp=sharing"
        )
    
    @dp.message(TaskForm.waiting_for_tz_url)
    async def process_tz_url(message: types.Message, state: FSMContext):
        data = await state.get_data()
        task_id = add_task(
            title=data["title"],
            description=data["description"],
            deadline=data["deadline"],
            tz_url=message.text,
            creator_chat_id=message.from_user.id
        )
        
        await state.clear()
        
        await message.answer(
            f"✅ Задача #{task_id} добавлена в очередь!\n\n"
            f"Название: {data['title']}\n"
            f"Дата запуска: {data['deadline']}"
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "📖 Справка\n\n"
            "/start - главное меню\n"
            "/new_task - создать новую задачу\n"
            "/mystatus - статус твоих задач\n"
            "/help - эта справка\n\n"
            "Как работать:\n"
            "1️⃣ Создай задачу через /new_task\n"
            "2️⃣ Укажи название, описание и приоритет\n"
            "3️⃣ Используй /mystatus чтобы следить за статусом\n"
            "4️⃣ Получай уведомления об изменениях"
        )


def register_bot2_handlers(dp: Dispatcher, bot2: Bot):
    """Register Bot 2 handlers"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "� **Добро пожаловать в таск-трекер!**\n\n"
            "Я помогаю управлять и отслеживать задачи на разработку веб-страниц.\n\n"
            "**Возможности:**\n"
            "📋 Просмотр всех задач\n"
            "✋ Взятие задачи себе\n"
            "🔄 Изменение статуса\n"
            "📊 Статистика по статусам\n"
            "🔔 Уведомления авторам\n\n"
            "**Команды:**\n"
            "/tasks - список всех задач\n"
            "/status - статистика\n"
            "/manage - управление задачами\n"
            "/help - справка\n\n"
            "Нажми /tasks чтобы начать работу 👇",
            parse_mode="Markdown"
        )
    
    @dp.message(Command("tasks"))
    async def cmd_tasks(message: types.Message):
        tasks = get_all_tasks()
        
        if not tasks:
            await message.answer("📭 Нет задач")
            return
        
        text = "📋 **Все задачи:**\n\n"
        for task in tasks:
            status_emoji = STATUSES.get(task['status'], task['status'])
            text += f"#{task['id']} - {task['title']}\nСтатус: {status_emoji}\n\n"
        
        await message.answer(text, parse_mode="Markdown")
    
    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        """Show tasks grouped by status"""
        text = "📊 **Задачи по статусам:**\n\n"
        
        for status_key in STATUS_ORDER:
            status_name = STATUSES.get(status_key, status_key)
            tasks = get_tasks_by_status(status_key)
            text += f"{status_name}: {len(tasks)}\n"
        
        await message.answer(text, parse_mode="Markdown")
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "📖 **Справка для трекера**\n\n"
            "/tasks - все задачи\n"
            "/status - статистика по статусам\n"
            "/manage - управлять задачами\n"
            "/help - эта справка\n\n"
            "**Как работать:**\n"
            "1️⃣ /tasks - посмотри список задач\n"
            "2️⃣ Выбери задачу из списка\n"
            "3️⃣ Нажми ✋ Взять задачу (назначь себя)\n"
            "4️⃣ Меняй статус по ходу работы\n"
            "5️⃣ Автор задачи получит уведомление",
            parse_mode="Markdown"
        )
    
    @dp.message(Command("manage"))
    async def cmd_manage(message: types.Message):
        """Show inline buttons to manage tasks"""
        global ADMIN_USER_ID
        
        # Auto-set first admin
        if ADMIN_USER_ID is None:
            ADMIN_USER_ID = message.from_user.id
            logger.info(f"Admin auto-set to user {ADMIN_USER_ID} ({message.from_user.username})")
            await message.answer(
                f"✅ Ты назначен администратором трекера!\n"
                f"ID: {ADMIN_USER_ID}\n"
                f"Скопируй эту строку в .env если нужно:\n"
                f"`ADMIN_ID={ADMIN_USER_ID}`",
                parse_mode="Markdown"
            )
        elif message.from_user.id != ADMIN_USER_ID:
            await message.answer("❌ Только администратор может управлять задачами")
            return
        
        tasks = get_all_tasks()
        
        if not tasks:
            await message.answer("📭 Нет задач для управления")
            return
        
        buttons = []
        for task in tasks[:10]:  # Limit to 10
            buttons.append([
                InlineKeyboardButton(
                    text=f"#{task['id']} - {task['title'][:25]}",
                    callback_data=f"task_{task['id']}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("⚙️ Выбери задачу для управления:", reply_markup=kb)
    
    @dp.callback_query(F.data.startswith("task_"))
    async def process_task_callback(query: types.CallbackQuery):
        global ADMIN_USER_ID
        
        if query.from_user.id != ADMIN_USER_ID:
            await query.answer("❌ Только администратор может управлять задачами", show_alert=True)
            return
        
        task_id = int(query.data.split("_")[1])
        task = get_task_by_id(task_id)
        
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        status_emoji = STATUSES.get(task['status'], task['status'])
        assigned_text = f"👤 Назначена: {task.get('assigned_username')}" if task.get('assigned_to') else "👤 Не назначена"
        
        # Calculate priority based on deadline
        priority_emoji, priority_text, days = calculate_priority(task.get('deadline'))
        days_text = f" ({days} дней)" if days is not None else ""
        
        tz_link = f"<a href='{task.get('tz_url')}'>Описание ТЗ</a>" if task.get('tz_url') else "Нет ссылки"
        
        text = (
            f"📌 Задача #{task['id']}\n"
            f"Название: {task['title']}\n"
            f"Описание: {task['description'] or 'N/A'}\n"
            f"Статус: {status_emoji}\n"
            f"Приоритет: {priority_emoji} {priority_text}{days_text}\n"
            f"Дата запуска: {task.get('deadline', 'не указана')}\n"
            f"{tz_link}\n"
            f"{assigned_text}\n"
            f"Создана: {task['created_at']}"
        )
        
        buttons = [
            [InlineKeyboardButton(text="✋ Взять задачу", callback_data=f"assign_{task_id}")],
            [InlineKeyboardButton(text="⏳ В работе", callback_data=f"change_status_{task_id}_in_progress")],
            [InlineKeyboardButton(text="👀 На проверке", callback_data=f"change_status_{task_id}_review")],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"change_status_{task_id}_done")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"change_status_{task_id}_cancelled")],
        ]
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    
    @dp.callback_query(F.data.startswith("assign_"))
    async def process_assign_task(query: types.CallbackQuery):
        global ADMIN_USER_ID
        
        if ADMIN_USER_ID is None:
            ADMIN_USER_ID = query.from_user.id
        
        if query.from_user.id != ADMIN_USER_ID:
            await query.answer("❌ Только администратор может управлять задачами", show_alert=True)
            return
        
        task_id = int(query.data.split("_")[1])
        task = get_task_by_id(task_id)
        
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Assign task to current user
        username = query.from_user.username or f"User{query.from_user.id}"
        assign_task(task_id, query.from_user.id, username)
        
        await query.answer(f"✅ Ты взял(а) задачу #{task_id}", show_alert=True)
        
        # Refresh task view
        task = get_task_by_id(task_id)
        status_emoji = STATUSES.get(task['status'], task['status'])
        assigned_text = f"👤 Назначена: {task.get('assigned_username')}" if task.get('assigned_to') else "👤 Не назначена"
        
        # Recalculate priority
        priority_emoji, priority_text, days = calculate_priority(task.get('deadline'))
        days_text = f" ({days} дней)" if days is not None else ""
        
        tz_link = f"<a href='{task.get('tz_url')}'>Описание ТЗ</a>" if task.get('tz_url') else "Нет ссылки"
        
        text = (
            f"📌 Задача #{task['id']}\n"
            f"Название: {task['title']}\n"
            f"Описание: {task['description'] or 'N/A'}\n"
            f"Статус: {status_emoji}\n"
            f"Приоритет: {priority_emoji} {priority_text}{days_text}\n"
            f"Дата запуска: {task.get('deadline', 'не указана')}\n"
            f"{tz_link}\n"
            f"{assigned_text}\n"
            f"Создана: {task['created_at']}"
        )
        
        buttons = [
            [InlineKeyboardButton(text="✋ Взять задачу", callback_data=f"assign_{task_id}")],
            [InlineKeyboardButton(text="⏳ В работе", callback_data=f"change_status_{task_id}_in_progress")],
            [InlineKeyboardButton(text="👀 На проверке", callback_data=f"change_status_{task_id}_review")],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"change_status_{task_id}_done")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"change_status_{task_id}_cancelled")],
        ]
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    
    @dp.callback_query(F.data.startswith("change_status_"))
    async def process_status_change(query: types.CallbackQuery):
        global ADMIN_USER_ID
        
        if query.from_user.id != ADMIN_USER_ID:
            await query.answer("❌ Только администратор может менять статус", show_alert=True)
            return
        
        parts = query.data.split("_")
        task_id = int(parts[2])
        new_status = "_".join(parts[3:])
        
        task = get_task_by_id(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        old_status = task['status']
        update_task_status(task_id, new_status)
        
        old_emoji = STATUSES.get(old_status, old_status)
        new_emoji = STATUSES.get(new_status, new_status)
        
        notification = (
            f"🔔 Обновление статуса задачи\n\n"
            f"Задача #{task_id}: {task['title']}\n"
            f"Статус: {old_emoji} → {new_emoji}"
        )
        
        # Send notification to task creator (if set)
        try:
            if task['creator_chat_id']:
                await query.bot.send_message(task['creator_chat_id'], notification)
        except Exception as e:
            logger.error(f"Failed to send notification to creator: {e}")
        
        await query.answer(f"✅ Статус обновлён на {new_emoji}", show_alert=True)
        
        # Refresh task view with recalculated priority
        task = get_task_by_id(task_id)
        status_emoji = STATUSES.get(task['status'], task['status'])
        assigned_text = f"👤 Назначена: {task.get('assigned_username')}" if task.get('assigned_to') else "👤 Не назначена"
        
        # Recalculate priority
        priority_emoji, priority_text, days = calculate_priority(task.get('deadline'))
        days_text = f" ({days} дней)" if days is not None else ""
        
        tz_link = f"<a href='{task.get('tz_url')}'>Описание ТЗ</a>" if task.get('tz_url') else "Нет ссылки"
        
        text = (
            f"📌 Задача #{task['id']}\n"
            f"Название: {task['title']}\n"
            f"Описание: {task['description'] or 'N/A'}\n"
            f"Статус: {status_emoji}\n"
            f"Приоритет: {priority_emoji} {priority_text}{days_text}\n"
            f"Дата запуска: {task.get('deadline', 'не указана')}\n"
            f"{tz_link}\n"
            f"{assigned_text}\n"
            f"Создана: {task['created_at']}"
        )
        
        buttons = [
            [InlineKeyboardButton(text="✋ Взять задачу", callback_data=f"assign_{task_id}")],
            [InlineKeyboardButton(text="⏳ В работе", callback_data=f"change_status_{task_id}_in_progress")],
            [InlineKeyboardButton(text="👀 На проверке", callback_data=f"change_status_{task_id}_review")],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"change_status_{task_id}_done")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"change_status_{task_id}_cancelled")],
        ]
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

async def main():
    """Start both bots"""
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Build proxy URL if enabled
    proxy_url = None
    if MTPROTO_PROXY["enabled"]:
        proxy_url = f"mtproto://{MTPROTO_PROXY['secret']}@{MTPROTO_PROXY['server']}:{MTPROTO_PROXY['port']}"
        logger.info(f"MTProto proxy enabled: {MTPROTO_PROXY['server']}:{MTPROTO_PROXY['port']}")
    
    # Create bots and dispatchers with proxy support
    bot1 = Bot(token=BOT1_TOKEN, proxy=proxy_url) if proxy_url else Bot(token=BOT1_TOKEN)
    bot2 = Bot(token=BOT2_TOKEN, proxy=proxy_url) if proxy_url else Bot(token=BOT2_TOKEN)
    
    storage = MemoryStorage()
    
    dp1 = Dispatcher(storage=storage)
    dp2 = Dispatcher(storage=storage)
    
    # Setup handlers
    register_bot1_handlers(dp1)
    register_bot2_handlers(dp2, bot2)
    
    logger.info("Bot 1 (Task Receiver) started")
    logger.info("Bot 2 (Task Tracker) started")
    
    # Start polling for both bots
    try:
        await asyncio.gather(
            dp1.start_polling(bot1, allowed_updates=dp1.resolve_used_update_types()),
            dp2.start_polling(bot2, allowed_updates=dp2.resolve_used_update_types())
        )
    finally:
        await bot1.session.close()
        await bot2.session.close()

if __name__ == "__main__":
    asyncio.run(main())
