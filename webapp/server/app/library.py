"""문서 라이브러리 — 최종본이 있는 프로젝트를 날짜·유형·제목으로 찾게 목록을 만든다.

파일만 읽는다. 유형은 `최종/<유형>/<ID>` 폴더 이름, 날짜는 작업 ID 끝의 `_YYYYMMDD`,
원문 요청은 00의 `원문 요청:` 줄에서 온다(루트 CLAUDE.md §4). 파일은 바꾸지 않는다.
대표 파일이 작업물로 등록돼 있지 않으면(최종본이 유형 폴더로 옮겨진 뒤 다시 훑지 않은 웹 프로젝트) 실행 중이 아닐 때 한 번 다시 훑는다.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .db import Database
from .events import EventStore
from .files import FileStore
from .projects import ProjectService
from .scanner import ArtifactSync, artifact_id, final_dirs, scan

_ID_DATE = re.compile(r"_(\d{4})(\d{2})(\d{2})$")
_REQUEST = re.compile(r"^-\s*원문 요청\s*[:：]\s*(?P<text>.+?)\s*$", re.MULTILINE)
# 최종본 폴더에서 대표로 보여 줄 파일 순서: 문서 PDF → 슬라이드 PDF → 그 밖의 PDF → pptx
_PRIMARY_ORDER = (".pdf", ".pptx")
# 옛 평면 배치(최종/<ID>)는 유형 폴더가 없다
_UNSORTED_KIND = "미분류"


def _date_of(workspace_id: str, fallback: str) -> str:
    match = _ID_DATE.search(workspace_id)
    if match:
        try:
            return date(int(match[1]), int(match[2]), int(match[3])).isoformat()
        except ValueError:
            pass
    return fallback[:10]


def _request_of(work_root: Path, workspace_id: str) -> str:
    folder = work_root / "작업" / workspace_id / "workspace"
    briefs = sorted(folder.glob("00_*.md")) if folder.is_dir() else []
    if not briefs:
        return ""
    text = briefs[-1].read_text(encoding="utf-8", errors="replace")
    match = _REQUEST.search(text)
    return match["text"] if match else ""


def _primary_file(folder: Path, workspace_id: str) -> Path | None:
    files = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in _PRIMARY_ORDER]
    if not files:
        return None
    # 작업 ID와 같은 이름(문서 본문) → 작업 ID로 시작하는 이름(슬라이드) → 확장자 순서
    return min(files, key=lambda path: (path.stem != workspace_id, not path.stem.startswith(workspace_id),
                                        _PRIMARY_ORDER.index(path.suffix.lower()), path.name))


class LibraryService:
    def __init__(self, db: Database, events: EventStore, files: FileStore, projects: ProjectService):
        self._db = db
        self._files = files
        self._projects = projects
        self._sync = ArtifactSync(db, events, files)

    def documents(self) -> list[dict]:
        """최종본이 있는 프로젝트만, 최신 날짜부터."""
        rows = self._db.query("SELECT * FROM projects WHERE deleted_at IS NULL AND workspace_id IS NOT NULL")
        documents = []
        for row in rows:
            project = dict(row)
            work_root = self._projects.work_root(project)
            workspace_id = project["workspace_id"]
            for folder in final_dirs(work_root, workspace_id):
                documents.append(self._document(project, work_root, workspace_id, folder))
        return sorted(documents, key=lambda item: (item["date"], item["title"]), reverse=True)

    def _document(self, project: dict, work_root: Path, workspace_id: str, folder: Path) -> dict:
        kind = folder.parent.name if folder.parent.name != "최종" else _UNSORTED_KIND
        primary = _primary_file(folder, workspace_id)
        artifact = self._artifact_of(project, work_root, primary) if primary is not None else None
        return {
            "projectId": project["id"],
            "workspaceId": workspace_id,
            "title": project["display_name"],
            "request": _request_of(work_root, workspace_id),
            "kind": kind,
            "mode": "presentation" if kind == "발표" else (project["mode"] if project["mode"] != "auto" else "document"),
            "date": _date_of(workspace_id, project["created_at"]),
            "fileName": primary.name if primary else None,
            "artifactId": artifact,
        }

    def _artifact_of(self, project: dict, work_root: Path, primary: Path) -> str | None:
        try:
            candidate = artifact_id(project["id"], self._files.to_relative(primary))
        except ValueError:
            return None
        if not self._registered(candidate):
            if self._running(project["id"]):
                return None  # 실행 쪽이 훑는 중이다
            self._sync.sync(project, scan(work_root, project["workspace_id"], project["mode"]))
        return candidate if self._registered(candidate) else None

    def _registered(self, artifact: str) -> bool:
        return self._db.one("SELECT 1 FROM artifacts WHERE id = ?", (artifact,)) is not None

    def _running(self, project_id: str) -> bool:
        return self._db.one("SELECT 1 FROM runs WHERE project_id = ?"
                            " AND status IN ('running','awaiting_input','stopping')", (project_id,)) is not None
