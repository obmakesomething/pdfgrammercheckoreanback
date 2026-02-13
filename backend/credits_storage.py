#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Credits storage for Apps in Toss IAP-based monetization.

- Credits are integer units (e.g. 1 credit = 10,000 chars).
- Uses SQLite for persistence. In Railway, mount a volume and point CREDITS_DB_PATH to it.

Design goals:
- Idempotent grant by order_id
- Atomic consume
- Minimal PII: caller provides a pseudonymous user_id (e.g. device id). Do not log it.
"""

from __future__ import annotations

import os
import sqlite3
import datetime
from typing import Optional, Dict, Any


def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class CreditsStorage:
    def __init__(self, db_path: str):
        if not db_path:
            raise ValueError("db_path is required")

        self.db_path = db_path
        self._ensure_parent_dir()
        self._init_schema()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.db_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS credits (
                  user_id TEXT PRIMARY KEY,
                  balance INTEGER NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS iap_orders (
                  order_id TEXT PRIMARY KEY,
                  user_id TEXT NOT NULL,
                  sku TEXT NOT NULL,
                  credits_granted INTEGER NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS credit_ledger (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  delta INTEGER NOT NULL,
                  reason TEXT NOT NULL,
                  ref TEXT,
                  created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id);")

    def get_balance(self, user_id: str) -> int:
        if not user_id:
            return 0
        with self._connect() as conn:
            row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return 0
            return int(row["balance"])

    def _upsert_balance(self, conn: sqlite3.Connection, user_id: str, delta: int) -> int:
        now = _utc_now_iso()
        row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            new_balance = max(0, int(delta))
            conn.execute(
                "INSERT INTO credits(user_id, balance, updated_at) VALUES (?, ?, ?)",
                (user_id, new_balance, now),
            )
            return new_balance

        new_balance = int(row["balance"]) + int(delta)
        if new_balance < 0:
            new_balance = 0
        conn.execute(
            "UPDATE credits SET balance = ?, updated_at = ? WHERE user_id = ?",
            (new_balance, now, user_id),
        )
        return new_balance

    def add_credits(self, user_id: str, credits: int, reason: str, ref: Optional[str] = None) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required")
        credits = int(credits)
        if credits < 0:
            raise ValueError("credits must be >= 0")

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                bal = self._upsert_balance(conn, user_id, credits)
                conn.execute(
                    "INSERT INTO credit_ledger(user_id, delta, reason, ref, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, credits, reason, ref, _utc_now_iso()),
                )
                conn.execute("COMMIT;")
                return {"balance": bal}
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def grant_iap_order(self, user_id: str, order_id: str, sku: str, credits: int) -> Dict[str, Any]:
        """Idempotent grant. If order_id already exists, returns current balance without granting again."""
        if not user_id:
            raise ValueError("user_id is required")
        if not order_id:
            raise ValueError("order_id is required")
        if not sku:
            raise ValueError("sku is required")
        credits = int(credits)
        if credits <= 0:
            raise ValueError("credits must be > 0")

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                existing = conn.execute(
                    "SELECT order_id, credits_granted FROM iap_orders WHERE order_id = ?",
                    (order_id,),
                ).fetchone()
                if existing:
                    bal = self.get_balance(user_id)
                    conn.execute("COMMIT;")
                    return {
                        "granted": False,
                        "credits_added": 0,
                        "balance": bal,
                    }

                # Record order and update balance.
                conn.execute(
                    "INSERT INTO iap_orders(order_id, user_id, sku, credits_granted, created_at) VALUES (?, ?, ?, ?, ?)",
                    (order_id, user_id, sku, credits, _utc_now_iso()),
                )
                bal = self._upsert_balance(conn, user_id, credits)
                conn.execute(
                    "INSERT INTO credit_ledger(user_id, delta, reason, ref, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, credits, "iap_grant", order_id, _utc_now_iso()),
                )
                conn.execute("COMMIT;")
                return {
                    "granted": True,
                    "credits_added": credits,
                    "balance": bal,
                }
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def consume_credits(self, user_id: str, credits: int) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required")
        credits = int(credits)
        if credits <= 0:
            raise ValueError("credits must be > 0")

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
                bal = int(row["balance"]) if row else 0
                if bal < credits:
                    conn.execute("COMMIT;")
                    return {"consumed": False, "balance": bal}

                new_balance = bal - credits
                conn.execute(
                    "UPDATE credits SET balance = ?, updated_at = ? WHERE user_id = ?",
                    (new_balance, _utc_now_iso(), user_id),
                )
                conn.execute(
                    "INSERT INTO credit_ledger(user_id, delta, reason, ref, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, -credits, "consume", None, _utc_now_iso()),
                )
                conn.execute("COMMIT;")
                return {"consumed": True, "balance": new_balance}
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    def purge_user(self, user_id: str, keep_iap_order_ids: bool = True) -> Dict[str, Any]:
        """
        Delete/anonymize data for a user (used for "disconnect/unlink" callbacks).

        - Deletes credit balance + ledger for the user.
        - By default, keeps IAP order_id rows to prevent replay/double-grant,
          but anonymizes the `user_id` on those rows.
        """
        if not user_id:
            raise ValueError("user_id is required")

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                credits_deleted = conn.execute("DELETE FROM credits WHERE user_id = ?", (user_id,)).rowcount
                ledger_deleted = conn.execute("DELETE FROM credit_ledger WHERE user_id = ?", (user_id,)).rowcount

                orders_changed = 0
                if keep_iap_order_ids:
                    # Keep order_id rows to preserve idempotency, but remove per-user association.
                    orders_changed = conn.execute(
                        "UPDATE iap_orders SET user_id = ? WHERE user_id = ?",
                        ("deleted", user_id),
                    ).rowcount
                else:
                    orders_changed = conn.execute("DELETE FROM iap_orders WHERE user_id = ?", (user_id,)).rowcount

                conn.execute("COMMIT;")
                return {
                    "purged": True,
                    "credits_deleted": int(credits_deleted or 0),
                    "ledger_deleted": int(ledger_deleted or 0),
                    "orders_changed": int(orders_changed or 0),
                }
            except Exception:
                conn.execute("ROLLBACK;")
                raise
