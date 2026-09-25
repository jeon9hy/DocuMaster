"""ProjectService — 프로젝트·지시·레퍼런스·작업물·에이전트 설정의 메타데이터를 다룬다."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

from .config import Settings
from .db import Database, now_iso
from .events import EventStore
from .files import FileStore, UnsafePathError, reference_kind_of

REFERENCE_KIND_LABEL = {"pdf": "PDF", "image": "이미지", "url": "웹 링크", "text": "텍스트",
                        "markdown": "Markdown", "file": "파일"}
APPLY_POLICIES = {"nextStage", "currentAgent", "rerunStage"}
MODES = {"auto", "document", "presentation"}
MARKDOWN_PREVIEW_LIMIT = 2 * 1024 * 1024


class NotFoundError(LookupError):
    pass


class InvalidRequestError(ValueError):
    pass


class ProjectDeleteError(RuntimeError):
    pass


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / 1024 / 1024:.1f}MB"


def summary_of(row) -> dict:
    return {
        "id": row["id"],
        "name": row["display_name"],
        "description": row["description"],
        "mode": row["mode"],
        "readOnly": row["source"] == "imported",
        # 홈의 「최근 프로젝트」용: 마지막 이벤트 시각(없으면 만든 시각)
        "lastActivityAt": (row["last_activity_at"] if "last_activity_at" in row.keys() else None) or row["created_at"],
    }


class ProjectService:
    def __init__(self, settings: Settings, db: Database, events: EventStore, files: FileStore):
        self._settings = settings
        self._db = db
        self._events = events
        self._files = files

    # --- 프로젝트 --------------------------------------------------------------

    def list(self) -> list[dict]:
        rows = self._db.query(
            "SELECT p.*, (SELECT MAX(created_at) FROM events e WHERE e.project_id = p.id) AS last_activity_at"
            " FROM projects p WHERE p.deleted_at IS NULL ORDER BY p.source = 'imported', p.created_at DESC")
        return [summary_of(row) for row in rows]

    def get(self, project_id: str) -> dict:
        row = self._db.one("SELECT * FROM projects WHERE id = ? AND deleted_at IS NULL", (project_id,))
        if row is None:
            raise NotFoundError(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return dict(row)

    def work_root(self, project: dict) -> Path:
        return (self._settings.repo_root / project["work_root"]).resolve()

    def create(self, name: str, mode: str) -> dict:
        name = name.strip()
        if not name or len(name) > 100:
            raise InvalidRequestError("프로젝트 이름은 1~100자로 입력해 주세요.")
        if mode not in MODES:
            raise InvalidRequestError(f"알 수 없는 모드: {mode}")
        # fake는 샌드박스, claude는 저장소 루트(기존 작업/·최종/)에서 일한다.
        root = self._settings.sandbox_root if self._settings.orchestrator == "fake" else self._settings.repo_root
        root.mkdir(parents=True, exist_ok=True)
        project_id = f"p_{uuid.uuid4().hex[:12]}"
        now = now_iso()
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO projects (id, display_name, description, mode, work_root, source, created_at, updated_at)"
                " VALUES (?, ?, '', ?, ?, 'web', ?, ?)",
                (project_id, name, mode, root.relative_to(self._settings.repo_root).as_posix() or ".", now, now),
            )
        return summary_of(self._db.one("SELECT * FROM projects WHERE id = ?", (project_id,)))

    def delete(self, project_id: str) -> None:
        """프로젝트 전용 로컬 폴더를 지운 뒤 목록에서 숨긴다."""
        project = self.get(project_id)
        targets = [self._reference_dir(project)]
        workspace_id = project.get("workspace_id")
        if workspace_id:
            if Path(workspace_id).name != workspace_id or "/" in workspace_id or "\\" in workspace_id:
                raise UnsafePathError("잘못된 작업 폴더 이름입니다.")
            root = self.work_root(project)
            for folder in ("작업", "최종"):
                parent = self._files.ensure_allowed(root / folder)
                target = self._files.ensure_allowed(parent / workspace_id)
                if target.parent != parent:
                    raise UnsafePathError("프로젝트 폴더 밖은 삭제할 수 없습니다.")
                targets.append(target)

        # 모든 경로를 먼저 검증한 다음에만 삭제한다. DB 삭제는 파일 삭제가 모두 성공한 뒤 기록한다.
        safe_targets = []
        for target in targets:
            safe = self._files.ensure_allowed(target)
            if safe not in safe_targets:
                safe_targets.append(safe)
        try:
            for target in safe_targets:
                if target.exists():
                    if not target.is_dir():
                        raise OSError(f"프로젝트 폴더가 디렉터리가 아닙니다: {target.name}")
                    shutil.rmtree(target)
        except OSError as error:
            raise ProjectDeleteError("로컬 프로젝트 폴더를 삭제하지 못했습니다. 파일 사용 여부와 권한을 확인해 주세요.") from error

        self._db.execute("UPDATE projects SET deleted_at = ?, updated_at = ? WHERE id = ?",
                         (now_iso(), now_iso(), project_id))

    def snapshot(self, project_id: str) -> dict:
        """이벤트 전체 + lastEventSeq. 프론트엔드가 같은 reducer로 상태를 만든다."""
        project = self.get(project_id)
        events = self._events.list_after(project_id, 0)
        return {"project": summary_of(project), "events": events,
                "lastEventSeq": events[-1]["seq"] if events else 0}

    def require_writable(self, project: dict) -> None:
        if project["source"] == "imported":
            raise InvalidRequestError("기존 CLI 작업을 읽기 전용으로 연 프로젝트입니다.")

    # --- 지시 ------------------------------------------------------------------

    def add_message(self, project_id: str, text: str) -> None:
        project = self.get(project_id)
        self.require_writable(project)
        text = text.strip()
        if not text:
            raise InvalidRequestError("지시 내용이 비어 있습니다.")
        self._db.execute(
            "INSERT INTO user_messages (id, project_id, text, created_at) VALUES (?, ?, ?, ?)",
            (f"msg_{uuid.uuid4().hex[:12]}", project_id, text, now_iso()),
        )
        self._events.append(project_id, {"type": "user.message", "text": text})

    def take_undelivered_messages(self, project_id: str) -> list[str]:
        """아직 로이드에게 넘기지 않은 지시를 꺼내고 전달됨으로 표시한다."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id, text FROM user_messages WHERE project_id = ? AND delivered_at IS NULL ORDER BY created_at",
                (project_id,),
            ).fetchall()
            conn.executemany("UPDATE user_messages SET delivered_at = ? WHERE id = ?",
                             [(now_iso(), row["id"]) for row in rows])
        return [row["text"] for row in rows]

    def has_undelivered_messages(self, project_id: str) -> bool:
        return self._db.one("SELECT 1 FROM user_messages WHERE project_id = ? AND delivered_at IS NULL",
                            (project_id,)) is not None

    # --- 레퍼런스 ----------------------------------------------------------------

    def _reference_dir(self, project: dict) -> Path:
        # 기존 규칙상 사용자 참고자료는 자료/에 둔다(CLAUDE.md §4). 프로젝트마다 하위 폴더 하나.
        return self.work_root(project) / "자료" / f"web_{project['id']}"

    def _insert_reference(self, project_id: str, reference: dict, stored: dict) -> None:
        self._db.execute(
            'INSERT INTO "references" (id, project_id, name, kind, source_type, relative_path, url, mime_type, size,'
            " hash, parse_status, apply_policy, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?)",
            (reference["id"], project_id, reference["name"], reference["kind"], stored["source_type"],
             stored.get("relative_path"), stored.get("url"), stored.get("mime_type"), stored.get("size"),
             stored.get("hash"), reference["applyPolicy"], now_iso()),
        )
        self._events.append(project_id, {"type": "reference.added", "reference": reference})

    def _check_policy(self, apply_policy: str) -> None:
        if apply_policy not in APPLY_POLICIES:
            raise InvalidRequestError(f"알 수 없는 반영 방식: {apply_policy}")

    def add_file_reference(self, project_id: str, original_name: str, stream: BinaryIO,
                           mime_type: str | None, apply_policy: str) -> dict:
        project = self.get(project_id)
        self.require_writable(project)
        self._check_policy(apply_policy)
        path, size, digest = self._files.save_stream(self._reference_dir(project), original_name or "file", stream)
        kind = reference_kind_of(original_name)
        reference = {"id": f"ref_{uuid.uuid4().hex[:12]}", "name": original_name, "kind": kind,
                     "detail": f"{REFERENCE_KIND_LABEL[kind]} · {format_bytes(size)}",
                     "applyPolicy": apply_policy, "parseStatus": "ready"}
        self._insert_reference(project_id, reference, {
            "source_type": "file", "relative_path": self._files.to_relative(path),
            "mime_type": mime_type, "size": size, "hash": digest})
        return reference

    def add_text_reference(self, project_id: str, title: str, text: str, apply_policy: str) -> dict:
        project = self.get(project_id)
        self.require_writable(project)
        self._check_policy(apply_policy)
        if not title.strip() or not text.strip():
            raise InvalidRequestError("제목과 내용을 입력해 주세요.")
        path, size, digest = self._files.save_text(self._reference_dir(project), title.strip(), text)
        reference = {"id": f"ref_{uuid.uuid4().hex[:12]}", "name": title.strip(), "kind": "text",
                     "detail": f"텍스트 · {len(text):,}자", "applyPolicy": apply_policy, "parseStatus": "ready"}
        self._insert_reference(project_id, reference, {
            "source_type": "text", "relative_path": self._files.to_relative(path),
            "mime_type": "text/markdown", "size": size, "hash": digest})
        return reference

    def add_url_reference(self, project_id: str, url: str, title: str, apply_policy: str) -> dict:
        project = self.get(project_id)
        self.require_writable(project)
        self._check_policy(apply_policy)
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise InvalidRequestError("http(s):// 로 시작하는 주소를 입력해 주세요.")
        reference = {"id": f"ref_{uuid.uuid4().hex[:12]}", "name": title.strip() or parsed.netloc, "kind": "url",
                     "detail": f"웹 링크 · {parsed.netloc}", "applyPolicy": apply_policy, "parseStatus": "ready"}
        self._insert_reference(project_id, reference, {"source_type": "url", "url": url.strip()})
        return reference

    def remove_reference(self, project_id: str, reference_id: str) -> None:
        """목록에서만 뺀다(파일은 지우지 않는다 — 이미 로이드에게 넘어갔을 수 있다)."""
        project = self.get(project_id)
        self.require_writable(project)
        row = self._db.one('SELECT id FROM "references" WHERE id = ? AND project_id = ? AND deleted_at IS NULL',
                           (reference_id, project_id))
        if row is None:
            raise NotFoundError("레퍼런스를 찾을 수 없습니다.")
        self._db.execute('UPDATE "references" SET deleted_at = ? WHERE id = ?', (now_iso(), reference_id))
        self._events.append(project_id, {"type": "reference.removed", "referenceId": reference_id})

    def active_references(self, project_id: str) -> list[dict]:
        rows = self._db.query('SELECT * FROM "references" WHERE project_id = ? AND deleted_at IS NULL'
                              " ORDER BY created_at", (project_id,))
        return [dict(row) for row in rows]

    # --- 작업물 ------------------------------------------------------------------

    def artifact(self, project_id: str, artifact_id: str) -> dict:
        row = self._db.one("SELECT * FROM artifacts WHERE id = ? AND project_id = ?", (artifact_id, project_id))
        if row is None:
            raise NotFoundError("작업물을 찾을 수 없습니다.")
        return dict(row)

    def artifact_path(self, project_id: str, artifact_id: str) -> Path:
        row = self.artifact(project_id, artifact_id)
        try:
            path = self._files.resolve(row["relative_path"])
        except UnsafePathError as error:
            raise NotFoundError("허용되지 않은 경로입니다.") from error
        if not path.is_file():
            raise NotFoundError("파일이 없습니다(옮겨졌거나 삭제됨).")
        return path

    def artifact_list(self, project_id: str) -> list[dict]:
        self.get(project_id)
        rows = self._db.query("SELECT * FROM artifacts WHERE project_id = ? ORDER BY relative_path", (project_id,))
        return [{"id": row["id"], "name": row["name"], "fileType": row["file_type"], "stageId": row["stage_id"],
                 "agentId": row["agent_id"], "status": row["status"], "visibility": row["visibility"],
                 "relativePath": row["relative_path"], "mimeType": row["mime_type"], "size": row["size"],
                 "version": row["version"], "updatedAt": row["updated_at"]} for row in rows]

    def artifact_content(self, project_id: str, artifact_id: str, download_url: str) -> dict:
        row = self.artifact(project_id, artifact_id)
        path = self.artifact_path(project_id, artifact_id)
        file_type = row["file_type"]
        if file_type == "markdown":
            if path.stat().st_size > MARKDOWN_PREVIEW_LIMIT:
                return {"type": "file", "fileName": row["name"], "sizeBytes": path.stat().st_size,
                        "downloadUrl": download_url}
            return {"type": "markdown", "text": path.read_text(encoding="utf-8", errors="replace")}
        if file_type == "pdf":
            return {"type": "pdf", "title": row["name"], "subtitle": "", "pageCount": 0,
                    "src": f"{download_url}?inline=1"}
        if file_type == "image":
            return {"type": "image", "src": f"{download_url}?inline=1", "alt": row["name"]}
        return {"type": "file", "fileName": row["name"], "sizeBytes": path.stat().st_size,
                "downloadUrl": download_url}
