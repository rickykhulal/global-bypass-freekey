import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token (Loaded from .env or Render Environment Variables)
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Port for Render Web Service keep-alive
PORT = int(os.getenv("PORT", 8080))

# Primary Bot Owner ID
PRIMARY_OWNER_ID = 768020734231969793

# Default Bot Settings
DEFAULT_BOT_NAME = os.getenv("BOT_NAME", "GLOBAL BYPASS")
DEFAULT_ADMIN_IDS = [PRIMARY_OWNER_ID] + [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
DEFAULT_SUPPORT_URL = os.getenv("SUPPORT_URL", "https://discord.gg/")

# Database File Path
DB_PATH = os.getenv("DB_PATH", "database.db")
