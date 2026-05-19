import sqlite3
import json
from datetime import datetime
from config import DB_PATH

def init_db():
    """Initialize database with tasks table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_to INTEGER,
            assigned_username TEXT,
            creator_chat_id INTEGER,
            deadline DATE,
            tz_url TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def add_task(title: str, description: str, deadline: str = None, tz_url: str = None, creator_chat_id: int = None):
    """Add new task"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tasks (title, description, deadline, tz_url, status, creator_chat_id)
        VALUES (?, ?, ?, ?, 'new', ?)
    """, (title, description, deadline, tz_url, creator_chat_id))
    
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return task_id

def get_all_tasks():
    """Get all tasks"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cursor.fetchall()
    conn.close()
    
    return [dict(task) for task in tasks]

def get_task_by_id(task_id: int):
    """Get task by ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    
    return dict(task) if task else None

def update_task_status(task_id: int, status: str):
    """Update task status"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tasks 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, task_id))
    
    conn.commit()
    conn.close()

def get_tasks_by_status(status: str):
    """Get tasks by status"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
    tasks = cursor.fetchall()
    conn.close()
    
    return [dict(task) for task in tasks]

def assign_task(task_id: int, user_id: int, username: str = None):
    """Assign task to user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tasks 
        SET assigned_to = ?, assigned_username = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user_id, username, task_id))
    
    conn.commit()
    conn.close()

def get_user_tasks(creator_chat_id: int):
    """Get all tasks created by user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE creator_chat_id = ? ORDER BY created_at DESC", (creator_chat_id,))
    tasks = cursor.fetchall()
    conn.close()
    
    return [dict(task) for task in tasks]

def calculate_priority(deadline_str: str) -> tuple:
    """Calculate priority emoji and text based on deadline
    Returns (emoji, priority_text, days_left)
    """
    if not deadline_str:
        return ("🟢", "Низкий", None)
    
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_left = (deadline - today).days
        
        if days_left <= 7:
            return ("🔴", "Высокий", days_left)
        elif days_left <= 14:
            return ("🟡", "Средний", days_left)
        else:
            return ("🟢", "Низкий", days_left)
    except:
        return ("🟢", "Низкий", None)
