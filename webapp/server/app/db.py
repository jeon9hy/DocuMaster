"""SQLite = 관리대장(metadata · state · event log). 실제 문서 파일은 넣지 않는다."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id            TEXT PRIMARY KEY,
  display_name  TEXT NOT NULL,
  description   TEXT NOT NULL DEFAULT '',
  mode          TEXT NOT NULL CHECK (mode IN ('auto','document','presentation')),
  workspace_id  TEXT,                 -- 작업/<ID>의 ID. 오케스트레이터가 정하면 채운다
  work_root     TEXT NOT NULL,        -- 작업/·최종/·자료/가 있는 폴더(저장소 루트 기준 상대경로)
  source        TEXT NOT NULL CHECK (source IN ('web','imported')),
  session_id    TEXT,                 -- 로이드 세션 ID(--resume용)
  deleted_at    TEXT,                 -- 목록에서 삭제한 시각. 기록·파일은 남긴다(가져오기가 되살리지 않게)
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS projects_workspace ON projects(work_root, workspace_id)
  WHERE workspace_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS runs (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL REFERENCES projects(id),
  status          TEXT NOT NULL CHECK (status IN
                    ('running','awaiting_input','stopping','stopped','failed','completed')),
  current_stage   TEXT,
  current_agent   TEXT,
  stop_requested  INTEGER NOT NULL DEFAULT 0,
  pid             INTEGER,
  error_code      TEXT,
  actual_model    TEXT,                -- 실행 기록(stream-json init)에서 읽은 실제 모델
  cost_usd        REAL,                -- 턴마다 더한 비용(보고용, 확인 가능할 때만)
  agent_config_json TEXT,              -- 실행 시작 때 고정한 에이전트 설정(실행 중 바꿔도 이 실행에는 적용 안 됨)
  started_at      TEXT NOT NULL,
  finished_at     TEXT
);
CREATE INDEX IF NOT EXISTS runs_project ON runs(project_id, started_at);

CREATE TABLE IF NOT EXISTS events (
  id            TEXT PRIMARY KEY,
  project_id    TEXT NOT NULL REFERENCES projects(id),
  run_id        TEXT,
  seq           INTEGER NOT NULL,
  type          TEXT NOT NULL,
  payload_json  TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  UNIQUE (project_id, seq)
);

CREATE TABLE IF NOT EXISTS "references" (
  id             TEXT PRIMARY KEY,
  project_id     TEXT NOT NULL REFERENCES projects(id),
  name           TEXT NOT NULL,        -- 사용자가 준 원래 이름(표시용)
  kind           TEXT NOT NULL,
  source_type    TEXT NOT NULL CHECK (source_type IN ('file','url','text')),
  relative_path  TEXT,                 -- 저장소 루트 기준. url은 없음
  url            TEXT,
  mime_type      TEXT,
  size           INTEGER,
  hash           TEXT,                 -- sha256
  parse_status   TEXT NOT NULL CHECK (parse_status IN ('uploaded','processing','ready','error')),
  apply_policy   TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  deleted_at     TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  id             TEXT PRIMARY KEY,
  project_id     TEXT NOT NULL REFERENCES projects(id),
  run_id         TEXT,
  stage_id       TEXT NOT NULL,
  agent_id       TEXT NOT NULL,
  name           TEXT NOT NULL,
  relative_path  TEXT NOT NULL,        -- 저장소 루트 기준
  mime_type      TEXT NOT NULL,
  file_type      TEXT NOT NULL,
  status         TEXT NOT NULL,
  visibility     TEXT NOT NULL CHECK (visibility IN ('primary','internal')),
  version        INTEGER NOT NULL DEFAULT 1,
  size           INTEGER NOT NULL,
  mtime_ns       INTEGER NOT NULL,
  updated_at     TEXT NOT NULL,
  UNIQUE (project_id, relative_path)
);

CREATE TABLE IF NOT EXISTS agent_configs (
  project_id       TEXT NOT NULL REFERENCES projects(id),
  agent_id         TEXT NOT NULL,
  provider         TEXT NOT NULL,
  model_id         TEXT NOT NULL,
  reasoning_level  TEXT,
  updated_at       TEXT NOT NULL,
  PRIMARY KEY (project_id, agent_id)
);

CREATE TABLE IF NOT EXISTS pending_inputs (
  id               TEXT PRIMARY KEY,   -- promptId
  project_id       TEXT NOT NULL REFERENCES projects(id),
  run_id           TEXT,
  title            TEXT NOT NULL,
  message          TEXT NOT NULL,
  choices_json     TEXT NOT NULL,
  allow_free_text  INTEGER NOT NULL,
  status           TEXT NOT NULL CHECK (status IN ('open','answered','cancelled')),
  answer           TEXT,
  created_at       TEXT NOT NULL,
  answered_at      TEXT
);

-- Owner가 설정 화면에서 바꾼 모델·추론 강도(전역). 없는 에이전트는 기본 배치(contract.DEFAULT_AGENT_CONFIGS)를 쓴다.
CREATE TABLE IF NOT EXISTS agent_overrides (
  agent_id         TEXT PRIMARY KEY,
  provider         TEXT NOT NULL,
  model_id         TEXT NOT NULL,
  reasoning_level  TEXT,
  updated_at       TEXT NOT NULL
);

-- 로그인 세션. 쿠키의 원래 토큰은 저장하지 않고 sha256만 둔다.
CREATE TABLE IF NOT EXISTS sessions (
  token_hash  TEXT PRIMARY KEY,
  created_at  TEXT NOT NULL,
  expires_at  TEXT NOT NULL
);

-- 단일 Owner 프로필(PIN 해시는 여기 두지 않는다 — owner.json 또는 환경변수)
CREATE TABLE IF NOT EXISTS owner_profile (
  id           INTEGER PRIMARY KEY CHECK (id = 1),
  nickname     TEXT NOT NULL,
  avatar_file  TEXT,
  updated_at   TEXT NOT NULL
);

-- 사용자 지시. 실행 중에 보낸 지시는 현재 단계가 끝난 뒤(다음 턴에) 로이드에게 전달한다.
CREATE TABLE IF NOT EXISTS user_messages (
  id            TEXT PRIMARY KEY,
  project_id    TEXT NOT NULL REFERENCES projects(id),
  text          TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  delivered_at  TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Database:
    """연결 하나를 여러 스레드(요청·실행 감시)가 나눠 쓴다. 쓰기는 lock으로 한 번에 하나."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.lock = threading.RLock()
        with self.lock:
            self._conn.executescript(SCHEMA)
            self._migrate()
            self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def _migrate(self) -> None:
        """v1 DB에 새 열을 더한다(데이터는 그대로)."""
        columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(runs)")}
        if "agent_config_json" not in columns:
            self._conn.execute("ALTER TABLE runs ADD COLUMN agent_config_json TEXT")
        project_columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(projects)")}
        if "deleted_at" not in project_columns:
            self._conn.execute("ALTER TABLE projects ADD COLUMN deleted_at TEXT")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self._conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self.lock:
            return self._conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.transaction() as conn:
            conn.execute(sql, params)

    def close(self) -> None:
        with self.lock:
            self._conn.close()
