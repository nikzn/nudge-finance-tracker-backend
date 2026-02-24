from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    # For SQLite (default, no extra driver needed)
    # DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/nudge_finance_tracker"

    # For PostgreSQL (requires psycopg2-binary)
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/nudge_finance_tracker"

    # For MySQL (requires pymysql)
    # DATABASE_URL: str = "mysql+pymysql://user:password@localhost:3306/financedb"

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    PASSWORD_MIN_LENGTH: int = 8

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:8000","https://nudge-finance-tracker-frontend-fv1o.vercel.app","https://nudgefinancetracker.vercel.app"]

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    class Config:
        env_file = ".env"


settings = Settings()
