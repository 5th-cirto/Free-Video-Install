from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Universal Video Downloader API"
    app_version: str = "0.1.0"
    env: str = os.getenv("APP_ENV", "development")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    downloads_dir: Path = Path(os.getenv("DOWNLOADS_DIR", "./downloads")).resolve()
    max_parallel_downloads: int = int(os.getenv("MAX_PARALLEL_DOWNLOADS", "2"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
    sqlite_db_path: Path = Path(os.getenv("SQLITE_DB_PATH", "./data/app.db")).resolve()
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
    password_bcrypt_rounds: int = int(os.getenv("PASSWORD_BCRYPT_ROUNDS", "12"))
    free_daily_ai_limit: int = int(os.getenv("FREE_DAILY_AI_LIMIT", "5"))
    vip_duration_days: int = int(os.getenv("VIP_DURATION_DAYS", "30"))
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "").strip()
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    stripe_price_cny_1m: str = os.getenv("STRIPE_PRICE_CNY_1M", "").strip()
    stripe_success_url: str = os.getenv("STRIPE_SUCCESS_URL", "").strip()
    stripe_cancel_url: str = os.getenv("STRIPE_CANCEL_URL", "").strip()
    smtp_host: str = os.getenv("SMTP_HOST", "").strip()
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "").strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "").strip()
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    app_public_base_url: str = os.getenv("APP_PUBLIC_BASE_URL", "").strip() or os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()
    password_reset_token_expire_minutes: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))


settings = Settings()

