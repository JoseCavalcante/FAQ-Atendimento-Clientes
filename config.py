"""
Configuração centralizada da aplicação.
Todas as variáveis de ambiente são lidas aqui.
"""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
CHROMA_DIR = BASE_DIR / "chroma_data"


class Settings:
    """Configurações da aplicação carregadas do .env"""

    # ── App ──
    APP_NAME: str = os.getenv("APP_NAME", "Atendimento & Suporte IA")
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Database ──
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{BASE_DIR / 'saas.db'}"
    )

    # ── Auth / JWT ──
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ── LLM ──
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "100000"))

    # ── Storage ──
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")  # 'local' or 's3'
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

    # ── Embedding ──
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # ── CORS ──
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    ]

    # ── Billing / Plans ──
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # ── Plans Config ──
    PLANS = {
        "free": {
            "name": "Free",
            "max_documents": 3,
            "max_queries_per_month": 100,
            "max_file_size_mb": 5,
            "max_users": 1,
            "models": ["llama-3.3-70b-versatile"],
            "price_monthly": 0,
        },
        "pro": {
            "name": "Pro",
            "max_documents": 50,
            "max_queries_per_month": 5000,
            "max_file_size_mb": 50,
            "max_users": 10,
            "models": ["llama-3.3-70b-versatile", "gpt-4"],
            "price_monthly": 49.90,
        },
        "enterprise": {
            "name": "Enterprise",
            "max_documents": -1,  # ilimitado
            "max_queries_per_month": -1,
            "max_file_size_mb": 200,
            "max_users": -1,
            "models": ["all"],
            "price_monthly": 199.90,
        },
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
