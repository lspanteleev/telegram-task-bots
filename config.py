import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Tokens
BOT1_TOKEN = os.getenv("BOT1_TOKEN", "YOUR_BOT1_TOKEN_HERE")  # Task receiver bot
BOT2_TOKEN = os.getenv("BOT2_TOKEN", "YOUR_BOT2_TOKEN_HERE")  # Task tracker bot

# Admin IDs for notifications (auto-set on first /manage command)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) if os.getenv("ADMIN_ID", "0").isdigit() else 0
TASK_RECEIVER_CHAT_ID = int(os.getenv("TASK_RECEIVER_CHAT_ID", "0")) if os.getenv("TASK_RECEIVER_CHAT_ID", "0").isdigit() else 0

# SOCKS5 Proxy Configuration
SOCKS5_PROXY = {
    "server": os.getenv("SOCKS5_SERVER", "45.71.17.78"),
    "port": int(os.getenv("SOCKS5_PORT", "5432")),
    "username": os.getenv("SOCKS5_USER", "7e5zu"),
    "password": os.getenv("SOCKS5_PASS", "eov27j2v"),
    "enabled": os.getenv("SOCKS5_ENABLED", "True").lower() == "true"
}

# Database
DB_PATH = "tasks.db"
