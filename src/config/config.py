import os
import json
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

DYNAMIC_SETTINGS_PATH = "config/dynamic_settings.json"

class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_ALLOWED_USERS_JSON: str = "[]"

    @property
    def TELEGRAM_ALLOWED_USERS(self) -> List[int]:
        try:
            return json.loads(self.TELEGRAM_ALLOWED_USERS_JSON)
        except:
            return []

    # Gemini AI
    GEMINI_API_KEY: str = ""
    VISION_MODEL: str = "gemini-2.0-flash"
    NLP_MODEL: str = "gemini-2.0-flash"

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = "config/service_account.json"
    SPREADSHEET_ID: str = ""

    # Redis/Celery
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_DB: int = 1

    # Database
    DATABASE_URL: str = ""

    # Security
    X_API_KEY: str = "default_unsafe_key"
    
    # Traffic/Maps
    GOOGLE_MAPS_API_KEY: str = ""

    # Admin
    TARGET_USER_NAME: str = "CARLO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def load_dynamic_settings(self):
        """Overrides settings with values from dynamic_settings.json."""
        if os.path.exists(DYNAMIC_SETTINGS_PATH):
            try:
                with open(DYNAMIC_SETTINGS_PATH, "r") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key.upper()):
                            setattr(self, key.upper(), value)
                        elif hasattr(self, key):
                            setattr(self, key, value)
                logging.info(f"Dynamic settings loaded from {DYNAMIC_SETTINGS_PATH}")
            except Exception as e:
                logging.error(f"Error loading dynamic settings: {e}")

# Global instance
settings = Settings()
settings.load_dynamic_settings()
