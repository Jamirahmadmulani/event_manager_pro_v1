import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    
    SECRET_KEY = os.getenv("SECRET_KEY", "secret123")

    
    SQLALCHEMY_DATABASE_URI = os.getenv(
       "DATABASE_URL",
    "sqlite:///event_db.sqlite3"
)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_USERNAME")

    BLOCKED_DOMAINS = [
        "linkedin.com",
        "best-jobs-online.com",
        "monsterindia.com",
        "dare2compete.news"
    ]


