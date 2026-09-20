"""EventStore — 이벤트 추가(seq 부여) · 다시 보내기(replay) · SSE 구독자에게 전달.

이벤트 모양은 프론트엔드 src/types/events.ts와 같다. 타입을 더하면 두 곳을 함께 고친다
(tests/test_contract_sync.py가 두 목록이 같은지 확인한다).
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid

from .db import Database, now_iso

SCHEMA_VERSION = 1

EVENT_TYPES = frozenset(
    {
        "workflow.started",
        "workflow.stage.started",
        "workflow.stage.completed",
        "workflow.warning",
        "workflow.completed",
        "workflow.stop.requested",
        "workflow.stopped",
        "workflow.failed",
        "project.mode.decided",
        "validation.verdict",
        "user.input.required",
        "user.input.resolved",
        "agent.started",
        "agent.message",
        "agent.activity",
        "agent.completed",
        "agent.configured",
        "artifact.created",
        "artifact.updated",
        "handoff.created",
        "reference.added",
        "reference.removed",
        "user.message",
    }
)


def _to_event(row) -> dict:
    return {
        **json.loads(row["payload_json"]),
        "schemaVersion": SCHEMA_VERSION,
        "id": row["id"],
        "projectId": row["project_id"],
        "runId": row["run_id"],
        "seq": row["seq"],
        "at": row["created_at"],
    }


class _Subscriber:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.queue: asyncio.Queue[dict] = asyncio.Queue()


class EventStore:
    """seq는 프로젝트마다 1부터 계속 증가한다. 한 번 쓴 이벤트는 바꾸지 않는다."""

    def __init__(self, db: Database):
        self._db = db
        self._subscribers: dict[str, set[_Subscriber]] = {}
        self._sub_lock = threading.Lock()

    def append(self, project_id: str, payload: dict, run_id: str | None = None) -> dict:
        event_type = payload.get("type")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"알 수 없는 이벤트 타입: {event_type}")
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM events WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            event_id = f"evt_{uuid.uuid4().hex[:16]}"
            conn.execute(
                "INSERT INTO events (id, project_id, run_id, seq, type, payload_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_id, project_id, run_id, row["next"], event_type,
                 json.dumps(payload, ensure_ascii=False), now_iso()),
            )
            stored = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        event = _to_event(stored)
        self._publish(project_id, event)
        return event

    def list_after(self, project_id: str, after_seq: int = 0) -> list[dict]:
        rows = self._db.query(
            "SELECT * FROM events WHERE project_id = ? AND seq > ? ORDER BY seq", (project_id, after_seq)
        )
        return [_to_event(row) for row in rows]

    def last_seq(self, project_id: str) -> int:
        row = self._db.one("SELECT COALESCE(MAX(seq), 0) AS seq FROM events WHERE project_id = ?", (project_id,))
        return row["seq"]

    # --- 실시간 전달 -------------------------------------------------------------
    # 실행 감시는 별도 스레드에서 돌기 때문에, 구독자의 이벤트 루프로 안전하게 넘긴다.

    def subscribe(self, project_id: str) -> _Subscriber:
        subscriber = _Subscriber(asyncio.get_running_loop())
        with self._sub_lock:
            self._subscribers.setdefault(project_id, set()).add(subscriber)
        return subscriber

    def unsubscribe(self, project_id: str, subscriber: _Subscriber) -> None:
        with self._sub_lock:
            self._subscribers.get(project_id, set()).discard(subscriber)

    def _publish(self, project_id: str, event: dict) -> None:
        with self._sub_lock:
            subscribers = list(self._subscribers.get(project_id, ()))
        for subscriber in subscribers:
            try:
                subscriber.loop.call_soon_threadsafe(subscriber.queue.put_nowait, event)
            except RuntimeError:  # 루프가 이미 닫힘(연결 종료)
                self.unsubscribe(project_id, subscriber)
