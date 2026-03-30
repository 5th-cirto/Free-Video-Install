from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

import requests
import stripe

from api.config import settings
from api.services.sqlite_db import get_db_connection


class MembershipServiceError(RuntimeError):
    """Domain-level error for membership and billing operations."""


class QuotaExceededError(MembershipServiceError):
    """Raised when a free user's daily AI quota is exhausted."""

    def __init__(self, *, limit: int, used: int) -> None:
        self.limit = limit
        self.used = used
        super().__init__(f"AI daily quota exceeded: {used}/{limit}")


@dataclass(frozen=True)
class MembershipStatus:
    is_vip: bool
    plan_code: str
    valid_until: Optional[str]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_db_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _from_db_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _today_utc() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def _require_stripe_config() -> None:
    if not settings.stripe_secret_key:
        raise MembershipServiceError("STRIPE_SECRET_KEY is not configured.")
    if not settings.stripe_price_cny_1m:
        raise MembershipServiceError("STRIPE_PRICE_CNY_1M is not configured.")
    if not settings.stripe_success_url or not settings.stripe_cancel_url:
        raise MembershipServiceError("STRIPE_SUCCESS_URL or STRIPE_CANCEL_URL is not configured.")


def _setup_stripe() -> None:
    _require_stripe_config()
    stripe.api_key = settings.stripe_secret_key


def _stripe_client() -> stripe.StripeClient:
    """
    Build a Stripe client that ignores environment/system proxy variables.
    This avoids ProxyError failures in constrained desktop environments.
    """
    _require_stripe_config()
    session = requests.Session()
    session.trust_env = False
    http_client = stripe.RequestsClient(session=session, proxy=None, verify_ssl_certs=True)
    return stripe.StripeClient(
        settings.stripe_secret_key,
        http_client=http_client,
        max_network_retries=1,
    )


def _ensure_checkout_migration(conn: sqlite3.Connection) -> None:
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(membership_orders)").fetchall()}
    if "plan_code" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN plan_code TEXT NOT NULL DEFAULT 'vip_1m'")
    if "idempotency_key" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN idempotency_key TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key ON membership_orders(idempotency_key)")
    if "paid_at" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN paid_at TEXT")


def initialize_membership_migration() -> None:
    with get_db_connection() as conn:
        _ensure_checkout_migration(conn)


def _create_order_row(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    plan_code: str,
    idempotency_key: str,
) -> int:
    now = _to_db_time(_utc_now())
    cur = conn.execute(
        """
        INSERT INTO membership_orders(
            user_id, plan_code, status, currency, amount_cents, idempotency_key, created_at, updated_at
        )
        VALUES (?, ?, 'pending', 'cny', 0, ?, ?, ?)
        """,
        (user_id, plan_code, idempotency_key, now, now),
    )
    return int(cur.lastrowid)


def create_checkout_session(*, user_id: int, user_email: str, plan_code: str, idempotency_key: Optional[str]) -> dict[str, Any]:
    if plan_code != "vip_1m":
        raise MembershipServiceError("Unsupported plan_code.")
    client = _stripe_client()
    now = _utc_now()
    provided_key = (idempotency_key or "").strip()
    if provided_key:
        cache_key = f"{user_id}:{provided_key}"
    else:
        cache_key = f"{user_id}:auto:{uuid4().hex}"

    with get_db_connection() as conn:
        _ensure_checkout_migration(conn)

        existing = conn.execute(
            """
            SELECT id, stripe_checkout_session_id
            FROM membership_orders
            WHERE user_id = ? AND idempotency_key = ? AND status = 'pending'
            LIMIT 1
            """,
            (user_id, cache_key),
        ).fetchone()
        if existing and existing["stripe_checkout_session_id"]:
            session_id = str(existing["stripe_checkout_session_id"])
            checkout = client.v1.checkout.sessions.retrieve(session_id)
            return {
                "checkout_url": checkout.url,
                "checkout_session_id": checkout.id,
                "order_id": int(existing["id"]),
                "reused": True,
                "idempotency_key": cache_key,
            }

        try:
            order_id = _create_order_row(conn, user_id=user_id, plan_code=plan_code, idempotency_key=cache_key)
        except sqlite3.IntegrityError:
            # A concurrent request with the same idempotency key may have inserted first.
            existing_after_race = conn.execute(
                """
                SELECT id, stripe_checkout_session_id
                FROM membership_orders
                WHERE user_id = ? AND idempotency_key = ?
                LIMIT 1
                """,
                (user_id, cache_key),
            ).fetchone()
            if existing_after_race:
                session_id = str(existing_after_race["stripe_checkout_session_id"] or "")
                if session_id:
                    checkout = client.v1.checkout.sessions.retrieve(session_id)
                    return {
                        "checkout_url": checkout.url,
                        "checkout_session_id": checkout.id,
                        "order_id": int(existing_after_race["id"]),
                        "reused": True,
                        "idempotency_key": cache_key,
                    }
                raise MembershipServiceError("Checkout session is being created, please retry in a second.")
            raise MembershipServiceError("Failed to create checkout order due to idempotency conflict.")
        stripe_idempotency = f"checkout-order-{order_id}"
        session = client.v1.checkout.sessions.create(
            params={
                "mode": "payment",
                "line_items": [{"price": settings.stripe_price_cny_1m, "quantity": 1}],
                "success_url": settings.stripe_success_url,
                "cancel_url": settings.stripe_cancel_url,
                "customer_email": user_email,
                "client_reference_id": str(user_id),
                "metadata": {
                    "order_id": str(order_id),
                    "user_id": str(user_id),
                    "plan_code": plan_code,
                },
                "expires_at": int((now + timedelta(minutes=30)).timestamp()),
            },
            options={"idempotency_key": stripe_idempotency},
        )

        conn.execute(
            """
            UPDATE membership_orders
            SET stripe_checkout_session_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (session.id, _to_db_time(_utc_now()), order_id),
        )
        return {
            "checkout_url": session.url,
            "checkout_session_id": session.id,
            "order_id": order_id,
            "reused": False,
            "idempotency_key": cache_key,
        }


def create_offline_mock_order(*, user_id: int, plan_code: str, idempotency_key: Optional[str] = None) -> dict[str, Any]:
    if plan_code != "vip_1m":
        raise MembershipServiceError("Unsupported plan_code.")
    token = (idempotency_key or "").strip() or f"offline-{uuid4().hex}"
    cache_key = f"{user_id}:{token}"
    now = _to_db_time(_utc_now())
    fake_session_id = f"cs_mock_{uuid4().hex[:20]}"
    with get_db_connection() as conn:
        _ensure_checkout_migration(conn)
        existing = conn.execute(
            """
            SELECT id, stripe_checkout_session_id
            FROM membership_orders
            WHERE user_id = ? AND idempotency_key = ? AND status = 'pending'
            LIMIT 1
            """,
            (user_id, cache_key),
        ).fetchone()
        if existing:
            return {
                "order_id": int(existing["id"]),
                "checkout_session_id": str(existing["stripe_checkout_session_id"] or fake_session_id),
                "reused": True,
                "idempotency_key": cache_key,
            }

        cur = conn.execute(
            """
            INSERT INTO membership_orders(
                user_id, plan_code, status, currency, amount_cents, idempotency_key,
                stripe_checkout_session_id, created_at, updated_at
            )
            VALUES (?, ?, 'pending', 'cny', 1900, ?, ?, ?, ?)
            """,
            (user_id, plan_code, cache_key, fake_session_id, now, now),
        )
        return {
            "order_id": int(cur.lastrowid),
            "checkout_session_id": fake_session_id,
            "reused": False,
            "idempotency_key": cache_key,
        }


def get_membership_status(user_id: int) -> MembershipStatus:
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT plan_code, valid_until
            FROM membership_entitlements
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return MembershipStatus(is_vip=False, plan_code="free", valid_until=None)

    valid_until = str(row["valid_until"])
    is_vip = valid_until > _to_db_time(_utc_now())
    return MembershipStatus(is_vip=is_vip, plan_code=str(row["plan_code"]), valid_until=valid_until)


def list_membership_orders(user_id: int) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, plan_code, status, amount_cents, currency, paid_at, created_at, updated_at,
                   stripe_checkout_session_id, stripe_payment_intent_id
            FROM membership_orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "order_id": int(row["id"]),
                "plan_code": str(row["plan_code"] or "vip_1m"),
                "status": str(row["status"] or ""),
                "amount_cents": int(row["amount_cents"] or 0),
                "currency": str(row["currency"] or "cny"),
                "paid_at": str(row["paid_at"] or ""),
                "created_at": str(row["created_at"] or ""),
                "updated_at": str(row["updated_at"] or ""),
                "checkout_session_id": str(row["stripe_checkout_session_id"] or ""),
                "payment_intent_id": str(row["stripe_payment_intent_id"] or ""),
            }
        )
    return result


def consume_ai_summary_quota(user_id: int) -> dict[str, Any]:
    """
    Consume one AI summary quota unit for free users.

    VIP users bypass quota limits. Free users are limited by FREE_DAILY_AI_LIMIT.
    The increment is atomic per user+day.
    """
    limit = max(1, settings.free_daily_ai_limit)
    today = _today_utc()
    now = _to_db_time(_utc_now())

    with get_db_connection() as conn:
        status = get_membership_status(user_id)
        if status.is_vip:
            return {
                "is_vip": True,
                "limit": None,
                "used": None,
                "remaining": None,
                "usage_date": today,
            }

        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT id, usage_count
            FROM ai_usage_daily
            WHERE user_id = ? AND usage_date = ?
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()

        if not row:
            conn.execute(
                """
                INSERT INTO ai_usage_daily(user_id, usage_date, usage_count, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                """,
                (user_id, today, now, now),
            )
            used = 1
        else:
            current = int(row["usage_count"])
            if current >= limit:
                raise QuotaExceededError(limit=limit, used=current)
            used = current + 1
            conn.execute(
                """
                UPDATE ai_usage_daily
                SET usage_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (used, now, int(row["id"])),
            )

        return {
            "is_vip": False,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
            "usage_date": today,
        }


def preview_ai_summary_quota(user_id: int) -> dict[str, Any]:
    """
    Read current quota state without consuming usage.
    """
    limit = max(1, settings.free_daily_ai_limit)
    today = _today_utc()
    status = get_membership_status(user_id)
    if status.is_vip:
        return {
            "is_vip": True,
            "limit": None,
            "used": None,
            "remaining": None,
            "usage_date": today,
            "exceeded": False,
        }

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT usage_count
            FROM ai_usage_daily
            WHERE user_id = ? AND usage_date = ?
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()
    used = int(row["usage_count"]) if row else 0
    return {
        "is_vip": False,
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "usage_date": today,
        "exceeded": used >= limit,
    }


def _record_webhook_if_new(conn: sqlite3.Connection, *, event_id: str, event_type: str, payload: str) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO billing_webhook_events(stripe_event_id, event_type, processed, payload, created_at)
            VALUES (?, ?, 0, ?, ?)
            """,
            (event_id, event_type, payload, _to_db_time(_utc_now())),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def _grant_or_extend_membership(conn: sqlite3.Connection, *, user_id: int, order_id: int, plan_code: str) -> dict[str, str]:
    now = _utc_now()
    now_db = _to_db_time(now)
    days = max(1, settings.vip_duration_days)

    row = conn.execute(
        """
        SELECT id, valid_until
        FROM membership_entitlements
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row and row["valid_until"]:
        current_until = _from_db_time(str(row["valid_until"]))
        base = current_until if current_until > now else now
        valid_from = now_db
        valid_until = _to_db_time(base + timedelta(days=days))
        conn.execute(
            """
            UPDATE membership_entitlements
            SET plan_code = ?, valid_from = ?, valid_until = ?, source_order_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (plan_code, valid_from, valid_until, order_id, now_db, int(row["id"])),
        )
        return {"valid_from": valid_from, "valid_until": valid_until}

    valid_from = now_db
    valid_until = _to_db_time(now + timedelta(days=days))
    conn.execute(
        """
        INSERT INTO membership_entitlements(user_id, plan_code, valid_from, valid_until, source_order_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, plan_code, valid_from, valid_until, order_id, now_db, now_db),
    )
    return {"valid_from": valid_from, "valid_until": valid_until}


def verify_and_construct_event(payload: bytes, signature: str) -> stripe.Event:
    if not settings.stripe_webhook_secret:
        raise MembershipServiceError("STRIPE_WEBHOOK_SECRET is not configured.")
    _setup_stripe()
    try:
        return stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError as exc:
        raise MembershipServiceError("Invalid Stripe signature.") from exc
    except ValueError as exc:
        raise MembershipServiceError("Invalid webhook payload.") from exc


def process_webhook_event(event: stripe.Event, raw_payload: bytes) -> dict[str, Any]:
    event_id = str(event.id)
    event_type = str(event.type)
    payload_text = raw_payload.decode("utf-8", errors="replace")

    with get_db_connection() as conn:
        _ensure_checkout_migration(conn)
        inserted = _record_webhook_if_new(conn, event_id=event_id, event_type=event_type, payload=payload_text)
        if not inserted:
            return {"ok": True, "duplicate": True, "event_type": event_type}

        result: dict[str, Any] = {"ok": True, "duplicate": False, "event_type": event_type}
        if event_type == "checkout.session.completed":
            session = event.data.object
            payment_status = str(getattr(session, "payment_status", "") or "")
            if payment_status != "paid":
                result["ignored_reason"] = "payment_not_paid"
            else:
                metadata_raw = getattr(session, "metadata", {}) or {}
                if hasattr(metadata_raw, "to_dict_recursive"):
                    metadata = metadata_raw.to_dict_recursive()
                elif isinstance(metadata_raw, dict):
                    metadata = metadata_raw
                else:
                    metadata = {}
                user_id = int(str(metadata.get("user_id") or getattr(session, "client_reference_id") or "0"))
                order_id = int(str(metadata.get("order_id") or "0"))
                plan_code = str(metadata.get("plan_code") or "vip_1m")
                if user_id <= 0:
                    raise MembershipServiceError("Invalid user_id in checkout metadata.")

                order_row = None
                if order_id > 0:
                    order_row = conn.execute(
                        "SELECT id, status FROM membership_orders WHERE id = ? LIMIT 1",
                        (order_id,),
                    ).fetchone()
                if not order_row:
                    order_row = conn.execute(
                        """
                        SELECT id, status
                        FROM membership_orders
                        WHERE stripe_checkout_session_id = ?
                        LIMIT 1
                        """,
                        (str(session.id),),
                    ).fetchone()
                if not order_row:
                    raise MembershipServiceError("Order not found for checkout session.")

                db_order_id = int(order_row["id"])
                if str(order_row["status"]) != "paid":
                    now_db = _to_db_time(_utc_now())
                    conn.execute(
                        """
                        UPDATE membership_orders
                        SET status = 'paid',
                            stripe_checkout_session_id = ?,
                            stripe_payment_intent_id = ?,
                            amount_cents = ?,
                            currency = ?,
                            paid_at = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            str(session.id),
                            str(getattr(session, "payment_intent", "") or ""),
                            int(getattr(session, "amount_total", 0) or 0),
                            str(getattr(session, "currency", "cny") or "cny").lower(),
                            now_db,
                            now_db,
                            db_order_id,
                        ),
                    )
                    window = _grant_or_extend_membership(
                        conn,
                        user_id=user_id,
                        order_id=db_order_id,
                        plan_code=plan_code,
                    )
                    result["granted"] = window
                else:
                    result["already_paid"] = True

        conn.execute(
            """
            UPDATE billing_webhook_events
            SET processed = 1, processed_at = ?
            WHERE stripe_event_id = ?
            """,
            (_to_db_time(_utc_now()), event_id),
        )
        return result


def create_mock_paid_event_payload(*, checkout_session_id: str, order_id: int, user_id: int, event_id: Optional[str] = None) -> tuple[str, bytes]:
    # Offline testing helper to validate idempotency and entitlement logic without calling Stripe.
    payload = {
        "id": event_id or f"evt_mock_{uuid4().hex[:18]}",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": checkout_session_id,
                "object": "checkout.session",
                "payment_status": "paid",
                "payment_intent": f"pi_mock_{uuid4().hex[:18]}",
                "amount_total": 1900,
                "currency": "cny",
                "client_reference_id": str(user_id),
                "metadata": {
                    "order_id": str(order_id),
                    "user_id": str(user_id),
                    "plan_code": "vip_1m",
                },
            }
        },
    }
    text = json.dumps(payload, ensure_ascii=False)
    return payload["id"], text.encode("utf-8")

