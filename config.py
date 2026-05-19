import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Tokens
BOT1_TOKEN = os.getenv("BOT1_TOKEN", "YOUR_BOT1_TOKEN_HERE")  # Task receiver bot
BOT2_TOKEN = os.getenv("BOT2_TOKEN", "YOUR_BOT2_TOKEN_HERE")  # Task tracker bot

# Admin IDs for notifications (auto-set on first /manage command)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) if os.getenv("ADMIN_ID", "0").isdigit() else 0
TASK_RECEIVER_CHAT_ID = int(os.getenv("TASK_RECEIVER_CHAT_ID", "0")) if os.getenv("TASK_RECEIVER_CHAT_ID", "0").isdigit() else 0

# MTProto Proxy Configuration
MTPROTO_PROXY = {
    "server": os.getenv("MTPROTO_SERVER", "tgnn.live"),
    "port": int(os.getenv("MTPROTO_PORT", "8443")),
    "secret": os.getenv("MTPROTO_SECRET", "ee9e1dde0de02a2e7c22d10e2fff84101374676e6e2e6c697665"),
    "enabled": os.getenv("MTPROTO_ENABLED", "True").lower() == "true"
}

# Database
DB_PATH = "tasks.db"
