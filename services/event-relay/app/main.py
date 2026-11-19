"""Tiny persistent event relay for local development (no RabbitMQ needed).

Durable append-only queue backed by SQLite. Publishers POST events; consumers
poll by exchange and monotonic id. Each microservice keeps its own database, so
this relay is the only shared transport.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = Path(os.getenv("RELAY_DB", "/tmp/themis-relay.db")).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with _lock, connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                routing_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                message_id TEXT,
                correlation_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_exchange_id "
            "ON events(exchange, id)"
        )


init_db()
app = FastAPI(title="Themis Event Relay", version="0.1.0")


class PublishRequest(BaseModel):
    exchange: str
    routing_key: str
    payload: dict[str, Any]
    message_id: Optional[str] = None
    correlation_id: Optional[str] = None


@app.post("/publish")
def publish(body: PublishRequest) -> dict[str, int]:
    with _lock, connect() as connection:
        cursor = connection.execute(
            "INSERT INTO events(exchange, routing_key, payload, message_id, "
            "correlation_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                body.exchange,
                body.routing_key,
                json.dumps(body.payload, default=str),
                body.message_id,
                body.correlation_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return {"id": int(cursor.lastrowid)}


@app.get("/poll")
def poll(
    exchange: str, after_id: int = 0, limit: int = 100
) -> dict[str, list[dict[str, Any]]]:
    limit = max(1, min(limit, 500))
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, exchange, routing_key, payload, message_id, "
            "correlation_id, created_at FROM events "
            "WHERE exchange = ? AND id > ? ORDER BY id LIMIT ?",
            (exchange, after_id, limit),
        ).fetchall()
    return {
        "events": [
            {
                "id": row["id"],
                "exchange": row["exchange"],
                "routing_key": row["routing_key"],
                "payload": json.loads(row["payload"]),
                "message_id": row["message_id"],
                "correlation_id": row["correlation_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "event-relay", "db": str(DB_PATH)}
