import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.getenv("DB_HOST")
    MYSQL_PORT = int(os.getenv("DB_PORT", "3306"))
    MYSQL_USER = os.getenv("DB_USER")
    MYSQL_PASSWORD = os.getenv("DB_PASS")
    MYSQL_DB = os.getenv("DB_NAME")

    # Set SECRET_KEY to a long random value in your local .env and deployment settings.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))
