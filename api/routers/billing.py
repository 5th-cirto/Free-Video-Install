from __future__ import annotations

import json

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from api.config import settings
from api.schemas import BillingCheckoutRequest
from api.services.auth_service import AuthUser, get_current_user
from api.services.membership_service import (
    MembershipServiceError,
    create_checkout_session,
    create_mock_paid_event_payload,
    create_offline_mock_order,
    list_membership_orders,
    get_membership_status,
    process_webhook_event,
    verify_and_construct_event,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout-session")
def create_checkout(payload: BillingCheckoutRequest, current_user: AuthUser = Depends(get_current_user)) -> dict:
    try:
        result = create_checkout_session(
            user_id=current_user.user_id,
            user_email=current_user.email,
            plan_code=payload.plan_code,
            idempotency_key=payload.idempotency_key,
        )
        return {"success": True, "message": "checkout session created", "data": result}
    except MembershipServiceError as exc:
        message = str(exc)
        code = status.HTTP_400_BAD_REQUEST
        if "not configured" in message.lower():
            code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=code, detail=message) from exc
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Stripe request failed: {exc.user_message or str(exc)}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Checkout session failed unexpectedly: {exc}") from exc


@router.get("/membership-status")
def membership_status(current_user: AuthUser = Depends(get_current_user)) -> dict:
    info = get_membership_status(current_user.user_id)
    return {
        "success": True,
        "message": "ok",
        "data": {
            "is_vip": info.is_vip,
            "plan_code": info.plan_code,
            "valid_until": info.valid_until,
        },
    }


@router.get("/orders")
def list_orders(current_user: AuthUser = Depends(get_current_user)) -> dict:
    try:
        orders = list_membership_orders(current_user.user_id)
        return {"success": True, "message": "ok", "data": {"orders": orders}}
    except MembershipServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="", alias="Stripe-Signature")) -> dict:
    if not stripe_signature.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header.")

    payload = await request.body()
    try:
        event = verify_and_construct_event(payload, stripe_signature)
        result = process_webhook_event(event, payload)
        return {"success": True, "message": "ok", "data": result}
    except MembershipServiceError as exc:
        text = str(exc)
        code = status.HTTP_400_BAD_REQUEST
        if "not configured" in text.lower():
            code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=code, detail=text) from exc
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stripe webhook processing failed: {exc.user_message or str(exc)}") from exc


@router.post("/mock/webhook-paid")
def mock_paid_webhook(current_user: AuthUser = Depends(get_current_user)) -> dict:
    if settings.env.lower() == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mock webhook is disabled in production.")
    try:
        mock_order = create_offline_mock_order(
            user_id=current_user.user_id,
            plan_code="vip_1m",
            idempotency_key=f"mock-{current_user.user_id}",
        )
        _, payload_bytes = create_mock_paid_event_payload(
            checkout_session_id=str(mock_order["checkout_session_id"]),
            order_id=int(mock_order["order_id"]),
            user_id=current_user.user_id,
        )
        event = stripe.Event.construct_from(json.loads(payload_bytes.decode("utf-8")), "")
        processed = process_webhook_event(event, payload_bytes)
        return {"success": True, "message": "mock webhook processed", "data": processed}
    except MembershipServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Stripe request failed: {exc.user_message or str(exc)}") from exc
