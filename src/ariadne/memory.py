"""Opt-in, local knowledge notes with simple provenance and lifecycle state."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    id: str
    content: str
    source: str
    recorded_at: str
    evidence_status: str
    lifecycle_state: str


class MemoryStore:
    """Small SQLite store for facts the user explicitly asks Ariadne to save."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS knowledge_records (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    evidence_status TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL
                )"""
            )

    def save(self, content: str, source: str = "user-provided") -> KnowledgeRecord:
        text = content.strip()
        if not text:
            raise ValueError("memory content must not be empty")
        record = KnowledgeRecord(
            id=uuid4().hex[:12],
            content=text,
            source=source,
            recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            evidence_status="user-provided",
            lifecycle_state="active",
        )
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO knowledge_records
                   (id, content, source, recorded_at, evidence_status, lifecycle_state)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.content,
                    record.source,
                    record.recorded_at,
                    record.evidence_status,
                    record.lifecycle_state,
                ),
            )
        return record

    def search(self, query: str, limit: int = 10) -> list[KnowledgeRecord]:
        term = query.strip()
        if not term:
            raise ValueError("search query must not be empty")
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """SELECT id, content, source, recorded_at, evidence_status, lifecycle_state
                   FROM knowledge_records
                   WHERE lifecycle_state = 'active' AND content LIKE ?
                   ORDER BY recorded_at DESC LIMIT ?""",
                (f"%{term}%", max(1, min(limit, 100))),
            ).fetchall()
        return [KnowledgeRecord(*row) for row in rows]

    def retire(self, record_id: str) -> bool:
        """Hide a record from recall while preserving its audit history."""

        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE knowledge_records SET lifecycle_state = 'retired' WHERE id = ? AND lifecycle_state = 'active'",
                (record_id.strip(),),
            )
        return cursor.rowcount > 0

    def restore(self, record_id: str) -> bool:
        """Restore a previously retired record to normal recall."""

        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE knowledge_records SET lifecycle_state = 'active' WHERE id = ? AND lifecycle_state = 'retired'",
                (record_id.strip(),),
            )
        return cursor.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)
