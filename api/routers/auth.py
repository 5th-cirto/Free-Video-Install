from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas import (
    AuthEmailActionRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResetPasswordRequest,
)
from api.services.auth_service import (
    AuthServiceError,
    AuthUser,
    authenticate_user,
    get_current_user,
    request_password_reset,
    reset_password,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(payload: AuthRegisterRequest) -> dict:
    try:
        created = register_user(email=payload.email, password=payload.password)
        return {"success": True, "message": "register success", "data": created}
    except AuthServiceError as exc:
        message = str(exc)
        http_status = status.HTTP_409_CONFLICT if "already registered" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=http_status, detail=message) from exc


@router.post("/login")
def login(payload: AuthLoginRequest) -> dict:
    try:
        result = authenticate_user(email=payload.email, password=payload.password)
        return {"success": True, "message": "login success", "data": result}
    except AuthServiceError as exc:
        message = str(exc)
        if "not configured" in message.lower():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc


@router.get("/me")
def me(current_user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "success": True,
        "message": "ok",
        "data": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "membership": {
                "is_vip": current_user.is_vip,
                "vip_valid_until": current_user.vip_valid_until,
            },
        },
    }


@router.post("/request-password-reset")
def request_reset(payload: AuthEmailActionRequest) -> dict:
    try:
        request_password_reset(payload.email)
        return {"success": True, "message": "password reset email sent", "data": None}
    except AuthServiceError as exc:
        text = str(exc)
        code = status.HTTP_500_INTERNAL_SERVER_ERROR if "smtp" in text.lower() or "missing smtp" in text.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=text) from exc


@router.post("/reset-password")
def perform_reset(payload: AuthResetPasswordRequest) -> dict:
    try:
        reset_password(payload.token, payload.new_password)
        return {"success": True, "message": "password reset success", "data": None}
    except AuthServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
