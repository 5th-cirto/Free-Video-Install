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


settings = Settings()

