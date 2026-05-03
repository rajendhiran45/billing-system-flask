import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MYSQL_HOST=os.getenv("DB_HOST")
    MYSQL_USER=os.getenv("DB_USER")
    MYSQL_PASSWORD=os.getenv("DB_PASS")
    MYSQL_DB=os.getenv("DB_NAME")