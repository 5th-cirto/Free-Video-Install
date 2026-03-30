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


class AuthRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, description="User email")
    password: str = Field(..., min_length=8, max_length=128, description="Plain password")


class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, description="User email")
    password: str = Field(..., min_length=8, max_length=128, description="Plain password")


class AuthEmailActionRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, description="User email")


class AuthResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256, description="Password reset token from email link")
    new_password: str = Field(..., min_length=8, max_length=128, description="New plain password")


class BillingCheckoutRequest(BaseModel):
    plan_code: Literal["vip_1m"] = Field(default="vip_1m", description="Membership plan code")
    idempotency_key: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=80,
        description="Optional client idempotency key to prevent duplicate checkout creation.",
    )

