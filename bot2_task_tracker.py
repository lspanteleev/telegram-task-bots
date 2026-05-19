"""
BOT 2: Task Tracker
Manages task status updates and sends notifications to Bot 1
"""
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.callbacks.query import CallbackQuery
import logging

from database import get_all_tasks, get_task_by_id, update_task_status, get_tasks_by_status
from config import BOT2_TOKEN, ADMIN_ID, TASK_RECEIVER_CHAT_ID

logger = logging.getLogger(__name__)

STATUSES = {
    "new": "🆕 Новая",
    "in_progress": "⏳ В работе",
    "review": "👀 На проверке",
    "done": "✅ Готово",
    "cancelled": "❌ Отменено"
}

async def setup_bot2(dp: Dispatcher, bot: Bot):
    """Setup Bot 2 handlers"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "📊 Привет! Я таск-трекер для управления задачами.\n"
            "Используй команды ниже:"
        )
        await cmd_tasks(message)
    
    @dp.message(Command("tasks"))
    async def cmd_tasks(message: types.Message):
        tasks = get_all_tasks()
        
        if not tasks:
            await message.answer("📭 Нет задач")
            return
        
        text = "📋 **Все задачи:**\n\n"
        for task in tasks:
            text += f"#{task['id']} - {task['title']}\nСтатус: {STATUSES.get(task['status'], task['status'])}\n\n"
        
        await message.answer(text, parse_mode="Markdown")
    
    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        """Show tasks grouped by status"""
        text = "📊 **Задачи по статусам:**\n\n"
        
        for status_key, status_name in STATUSES.items():
            tasks = get_tasks_by_status(status_key)
            text += f"{status_name}: {len(tasks)}\n"
        
        await message.answer(text, parse_mode="Markdown")
    
    @dp.message(Command("manage"))
    async def cmd_manage(message: types.Message):
        """Show inline buttons to manage tasks"""
        tasks = get_all_tasks()
        
        if not tasks:
            await message.answer("📭 Нет задач для управления")
            return
        
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"#{task['id']} - {task['title'][:25]}", 
                                    callback_data=f"task_{task['id']}")] 
                for task in tasks[:10]  # Limit to 10 buttons
            ]
        )
        
        await message.answer("⚙️ Выбери задачу для управления:", reply_markup=kb)
    
    @dp.callback_query(F.data.startswith("task_"))
    async def process_task_callback(query: CallbackQuery):
        task_id = int(query.data.split("_")[1])
        task = get_task_by_id(task_id)
        
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        text = f"""
📌 **Задача #{task['id']}**
Название: {task['title']}
Описание: {task['description'] or 'N/A'}
Статус: {STATUSES.get(task['status'], task['status'])}
Приоритет: {task['priority']}
Создана: {task['created_at']}
"""
        
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏳ В работе", callback_data=f"change_status_{task_id}_in_progress")],
                [InlineKeyboardButton(text="👀 На проверке", callback_data=f"change_status_{task_id}_review")],
                [InlineKeyboardButton(text="✅ Готово", callback_data=f"change_status_{task_id}_done")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"change_status_{task_id}_cancelled")],
            ]
        )
        
        await query.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    
    @dp.callback_query(F.data.startswith("change_status_"))
    async def process_status_change(query: CallbackQuery, bot: Bot):
        parts = query.data.split("_")
        task_id = int(parts[2])
        new_status = "_".join(parts[3:])
        
        task = get_task_by_id(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        old_status = task['status']
        update_task_status(task_id, new_status)
        
        # Notify in Bot 1
        notification = (
            f"🔔 **Обновление статуса задачи**\n\n"
            f"Задача #{task_id}: {task['title']}\n"
            f"Статус: {STATUSES.get(old_status, old_status)} → {STATUSES.get(new_status, new_status)}"
        )
        
        try:
            await bot.send_message(TASK_RECEIVER_CHAT_ID, notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
        
        await query.answer(f"✅ Статус обновлён на {STATUSES.get(new_status, new_status)}", show_alert=True)
