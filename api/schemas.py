from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    message: str = "ok"
    data: Any = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    data: Any = None


class InspectRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Video URL")


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Video URL")
    format_id: Optional[str] = Field(default=None, description="yt-dlp format id")


class BatchDownloadRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, max_length=50)
    format_id: Optional[str] = Field(default=None, description="yt-dlp format id")


class SubtitleDownloadRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Video URL")
    language: Optional[str] = Field(default=None, description="Preferred subtitle language, e.g. zh-CN/en")
    format: Literal["txt", "srt", "vtt"] = Field(default="srt", description="Subtitle export format")

