"""기존 CLI 작업(작업/<ID>)을 읽기 전용 프로젝트로 가져온다. 파일은 읽기만 하고 바꾸지 않는다.

백엔드가 켜질 때마다 다시 본다 — 새 작업은 추가하고, 이미 가져온 작업은 바뀐 파일만 이벤트로 더한다.
"""

from __future__ import annotations

import re
import uuid

from . import contract
from .db import now_iso
from .scanner import ArtifactSync, scan

_TITLE = re.compile(r"^#\s*(?P<id>\S+)\s*[—-]\s*(?P<title>.+?)(?:\s*·\s*모드\s*:\s*(?P<mode>\w+))?\s*$")
_MODE = {"DOCUMENT": "document", "PRESENTATION": "presentation"}


def _describe(state_md: str, workspace_id: str) -> tuple[str, str | None]:
    first = state_md.splitlines()[0] if state_md else ""
    match = _TITLE.match(first)
    if not match:
        return workspace_id, None
    return match["title"].strip() or workspace_id, _MODE.get((match["mode"] or "").upper())


def import_existing_projects(services) -> list[str]:
    settings, db, events = services.settings, services.db, services.events
    root = settings.repo_root / "작업"
    if not root.is_dir():
        return []
    sync = ArtifactSync(db, events, services.files)
    touched = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        state = folder / "상태.md"
        if not state.is_file():
            continue
        row = db.one("SELECT * FROM projects WHERE work_root = '.' AND workspace_id = ?", (folder.name,))
        if row is None:
            title, mode = _describe(state.read_text(encoding="utf-8", errors="replace"), folder.name)
            project_id = f"p_{uuid.uuid4().hex[:12]}"
            now = now_iso()
            db.execute(
                "INSERT INTO projects (id, display_name, description, mode, workspace_id, work_root, source,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, '.', 'imported', ?, ?)",
                (project_id, title, f"작업/{folder.name} · 읽기 전용", mode or "auto", folder.name, now, now),
            )
            row = db.one("SELECT * FROM projects WHERE id = ?", (project_id,))
        elif row["source"] != "imported":
            continue  # 웹에서 만든 프로젝트의 작업 폴더 — 실행 쪽에서 관리한다
        elif row["deleted_at"]:
            continue  # 사용자가 목록에서 지운 작업 — 다시 가져오지 않는다
        project = dict(row)
        result = scan(settings.repo_root, folder.name, project["mode"])
        sync.sync(project, result)
        done = {r["payload_json"] for r in db.query(
            "SELECT payload_json FROM events WHERE project_id = ? AND type = 'workflow.stage.completed'",
            (project["id"],))}
        for stage in contract.STAGES:
            payload = {"type": "workflow.stage.completed", "stageId": stage}
            if stage in result.completed_stages() and not any(f'"{stage}"' in text for text in done):
                events.append(project["id"], payload)
        touched.append(project["id"])
    return touched
