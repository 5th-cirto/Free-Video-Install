from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers.ai_summary import router as ai_summary_router
from api.routers.video import router as video_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}


app.include_router(video_router)
app.include_router(ai_summary_router)

