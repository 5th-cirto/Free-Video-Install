from __future__ import annotations

import sqlite3
from pathlib import Path

from api.config import settings


def _connect() -> sqlite3.Connection:
    settings.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.sqlite_db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db_connection() -> sqlite3.Connection:
    return _connect()


def _ensure_membership_orders_columns(conn: sqlite3.Connection) -> None:
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(membership_orders)").fetchall()}
    if "plan_code" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN plan_code TEXT NOT NULL DEFAULT 'vip_1m'")
    if "idempotency_key" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN idempotency_key TEXT")
    if "paid_at" not in columns:
        conn.execute("ALTER TABLE membership_orders ADD COLUMN paid_at TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key ON membership_orders(idempotency_key)")


def _ensure_user_auth_columns(conn: sqlite3.Connection) -> None:
    user_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email_verified" not in user_columns:
        # Existing users are grandfathered as verified to avoid account lockout.
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            purpose TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_purpose ON auth_tokens(user_id, purpose)")


def init_sqlite_schema() -> None:
    # Initialize all baseline tables needed by auth, billing, and quota features.
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                email_verified INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS membership_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stripe_checkout_session_id TEXT UNIQUE,
                stripe_payment_intent_id TEXT UNIQUE,
                amount_cents INTEGER NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'cny',
                status TEXT NOT NULL DEFAULT 'pending',
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS membership_entitlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                plan_code TEXT NOT NULL DEFAULT 'vip_1m',
                valid_from TEXT NOT NULL,
                valid_until TEXT NOT NULL,
                source_order_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (source_order_id) REFERENCES membership_orders(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS billing_webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                processed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS ai_usage_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                usage_date TEXT NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, usage_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON membership_orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_usage_user_date ON ai_usage_daily(user_id, usage_date);
            """
        )
        _ensure_user_auth_columns(conn)
        _ensure_membership_orders_columns(conn)


def sqlite_db_path() -> Path:
    return settings.sqlite_db_path
