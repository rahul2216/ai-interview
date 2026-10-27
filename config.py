import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ai-mock-interview-secure-dev-key-2026-prod-grade")
    
    # Database
    db_url = os.getenv("DATABASE_URL", "sqlite:///mock_interview.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Application Config
    PROMPT_VERSION = "2.1.0-job-ready"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
    
    # CSRF
    WTF_CSRF_TIME_LIMIT = None  # No strict expiration during long interviews
