import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Gemini API Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBpzMyheU741kfH-w42cOMtqZhfYFrHfrY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 500))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "./data/conversations.db")


config = Config()


