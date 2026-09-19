"""작업 폴더를 읽어 작업물 메타데이터와 단계 진행을 이벤트로 바꾼다.

CLI 출력 문자열을 파싱하지 않는다. 계약된 파일(00~07 · 상태.md · 최종/<ID>)만 본다(지침서 §16).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from . import contract
from .db import Database, now_iso
from .events import EventStore
from .files import FileStore, file_type_of, mime_type_of

_SUMMARY = {
    "00": "사용자 요청 정리",
    "01": "조사 설계 · 기획",
    "02": "조사 결과",
    "03": "검증 질문",
    "04": "검증 응답",
    "05": "검증된 조사 결과 · 사실의 원천",
    "06": "세부 기획 · 구조의 원천",
    "07": "최종 원고",
}


@dataclass(frozen=True)
class FoundFile:
    path: Path
    stage_id: str
    agent_id: str
    visibility: str
    version: int
    summary: str
    number: str | None = None  # 계약 번호(workspace 파일만)


@dataclass
class ScanResult:
    numbers: set[str] = field(default_factory=set)
    has_visual: bool = False
    finished: bool = False
    workspace_exists: bool = False
    status: str = ""  # 상태.md의 `상태:` 줄
    verdict: str | None = None  # 최신 05의 판정
    files: list[FoundFile] = field(default_factory=list)

    def fingerprint(self) -> tuple:
        """진행 여부 비교용 — 파일 목록·수정 시각·상태 줄이 그대로면 진행이 없었던 것"""
        stamps = []
        for found in self.files:
            try:
                stamps.append((str(found.path), found.path.stat().st_mtime_ns))
            except OSError:
                continue
        return tuple(sorted(stamps)), self.status

    def completed_stages(self) -> set[str]:
        done = {stage for stage, number in
                (("requirements", "00"), ("planning", "01"), ("research", "02"),
                 ("validation", "05"), ("writing", "07")) if number in self.numbers}
        if self.finished:
            done.add("finalReview")
        return done


def workspace_dir(work_root: Path, workspace_id: str) -> Path:
    return work_root / "작업" / workspace_id


def scan(work_root: Path, workspace_id: str | None, mode: str) -> ScanResult:
    result = ScanResult()
    if not workspace_id:
        return result
    base = workspace_dir(work_root, workspace_id)
    state = base / "상태.md"
    result.workspace_exists = base.is_dir()
    if state.is_file():
        text = state.read_text(encoding="utf-8", errors="replace")
        result.finished = contract.is_finished(text)
        result.status = contract.status_line(text)

    parsed = []
    for path in sorted((base / "workspace").glob("*.md")):
        info = contract.workspace_file(path.name, mode)
        if info:
            parsed.append((path, info))
            result.numbers.add(info.number)
            result.has_visual |= info.number == "06" and "visual" in info.key
    latest = {}
    for _, info in parsed:
        latest[info.key] = max(latest.get(info.key, 0), info.version)
    for path, info in parsed:
        is_latest = latest[info.key] == info.version
        if is_latest and info.number == "05":
            first = contract.verdict_from_05(path.read_text(encoding="utf-8", errors="replace"))
            result.verdict = first[0] if first else None
        summary = "비주얼 기획" if "visual" in info.key else _SUMMARY[info.number]
        if info.number == "07" and "presentation" in info.key:
            summary = "발표팩"
        result.files.append(FoundFile(
            path=path, stage_id=info.stage_id, agent_id=info.agent_id,
            visibility="primary" if is_latest and info.number in contract.PRIMARY_NUMBERS else "internal",
            version=info.version,
            summary=summary + (f" · v{info.version:02d}" if info.version > 1 else "") + ("" if is_latest else " · 이전 버전"),
            number=info.number,
        ))

    for path in sorted((base / "output").glob("*")):
        if path.is_file():
            result.files.append(FoundFile(path, "finalReview", "loid", "internal", 1, "렌더 결과"))
    for path in sorted((work_root / "최종" / workspace_id).glob("*")):
        if path.is_file():
            result.files.append(FoundFile(path, "finalReview", "loid", "primary", 1, "최종본"))
    return result


def turn_outcome(result: ScanResult) -> tuple[str, str]:
    """로이드의 턴이 정상 종료된 뒤 무엇을 할지 — 구조화된 상태만 본다(문장이 질문형인지는 보지 않는다).

    completed: 상태.md = 완료
    needs_input: 상태 줄이 사용자 대기·중단·보류 / 05 판정이 blocked인데 06 전 / 작업 폴더가 아직 없음
                 (폴더 전에 턴이 끝나는 것은 모드 판정·이어 하기 확인뿐 — 대신 답하지 않는다)
    continue: 그 밖 — 같은 세션을 자동으로 이어 간다
    """
    if result.finished:
        return "completed", ""
    if not result.workspace_exists:
        return "needs_input", "로이드의 확인 요청 · 작업 시작 전"
    if contract.needs_user(result.status):
        return "needs_input", result.status
    if result.verdict == "blocked" and "06" not in result.numbers:
        return "needs_input", "검증 보류 — 확인 불가"
    return "continue", ""


def find_new_workspace(work_root: Path, since: float, claimed: set[str]) -> str | None:
    """실행을 시작한 뒤 새로 생긴 작업/<ID> 중 가장 최근 것(한 번에 한 실행만 하므로 모호하지 않다)."""
    root = work_root / "작업"
    if not root.is_dir():
        return None
    candidates = [
        path for path in root.iterdir()
        if path.is_dir() and path.name not in claimed and path.stat().st_ctime >= since - 2
    ]
    return max(candidates, key=lambda path: path.stat().st_ctime).name if candidates else None


# --- 단계 진행 -------------------------------------------------------------------


@dataclass(frozen=True)
class Progress:
    completed: frozenset[str] = frozenset()
    started: frozenset[str] = frozenset()
    worker: tuple[str, str] | None = None  # (stageId, agentId)

    @classmethod
    def resume_from(cls, result: ScanResult) -> "Progress":
        """새 실행: 끝난 단계만 안다. 지금 단계는 다시 '시작'으로 알린다(중지 때 대기로 돌아갔으므로)."""
        done = frozenset(result.completed_stages())
        return cls(completed=done, started=done)

    @classmethod
    def continuing(cls, result: ScanResult, mode: str) -> "Progress":
        """같은 실행을 이어 감(사용자 응답 뒤): 지금 단계·에이전트는 이미 알렸으므로 다시 알리지 않는다."""
        done = frozenset(result.completed_stages())
        if len(done) == len(contract.STAGES):
            return cls(completed=done, started=done)
        worker = contract.current_worker(result.numbers, mode, result.has_visual)
        return cls(completed=done, started=done | {worker[0]}, worker=worker)


def track_progress(previous: Progress, result: ScanResult, mode: str) -> tuple[Progress, list[dict]]:
    """이전 진행과 새 스캔을 비교해 단계·에이전트 이벤트를 만든다(순수 함수)."""
    payloads: list[dict] = []
    completed = set(previous.completed)
    started = set(previous.started)
    worker = previous.worker

    for stage in contract.STAGES:
        if stage in result.completed_stages() and stage not in completed:
            if stage not in started:  # 두 번 보는 사이에 시작과 끝이 다 지나간 단계도 '시작'을 먼저 알린다
                payloads.append({"type": "workflow.stage.started", "stageId": stage})
            if worker and worker[0] == stage:
                payloads.append({"type": "agent.completed", "agentId": worker[1]})
                worker = None
            payloads.append({"type": "workflow.stage.completed", "stageId": stage})
            completed.add(stage)
            started.add(stage)

    if len(completed) < len(contract.STAGES):
        next_worker = contract.current_worker(result.numbers, mode, result.has_visual)
        if next_worker != worker:
            if worker and worker[1] != next_worker[1]:
                payloads.append({"type": "agent.completed", "agentId": worker[1]})
                payloads.append({"type": "handoff.created", "fromAgentId": worker[1], "toAgentId": next_worker[1]})
            if next_worker[0] not in started:
                payloads.append({"type": "workflow.stage.started", "stageId": next_worker[0]})
                started.add(next_worker[0])
            if not worker or worker[1] != next_worker[1]:
                payloads.append({"type": "agent.started", "agentId": next_worker[1], "stageId": next_worker[0]})
            worker = next_worker

    return Progress(frozenset(completed), frozenset(started), worker), payloads


# --- 작업물 동기화 -----------------------------------------------------------------


def artifact_id(project_id: str, relative_path: str) -> str:
    return "art_" + hashlib.sha1(f"{project_id}:{relative_path}".encode()).hexdigest()[:16]


class ArtifactSync:
    """스캔 결과와 artifacts 테이블을 비교해 새로 생기거나 바뀐 작업물만 이벤트로 낸다."""

    def __init__(self, db: Database, events: EventStore, files: FileStore):
        self._db = db
        self._events = events
        self._files = files

    def sync(self, project: dict, result: ScanResult, run_id: str | None = None) -> None:
        known = {row["relative_path"]: row for row in self._db.query(
            "SELECT * FROM artifacts WHERE project_id = ?", (project["id"],))}
        for found in result.files:
            try:
                path = self._files.ensure_allowed(found.path)
                stat = path.stat()
            except (OSError, ValueError):
                continue
            relative = self._files.to_relative(path)
            row = known.get(relative)
            if row is None:
                self._create(project, found, relative, stat, run_id)
            elif row["mtime_ns"] != stat.st_mtime_ns or row["size"] != stat.st_size:
                self._touch(project, row, found, stat, run_id, announce=True)
            elif row["visibility"] != found.visibility:
                self._touch(project, row, found, stat, run_id, announce=False)

    def _create(self, project: dict, found: FoundFile, relative: str, stat, run_id: str | None) -> None:
        artifact = {
            "id": artifact_id(project["id"], relative),
            "name": found.path.name,
            "fileType": file_type_of(found.path),
            "status": "latest",
            "stageId": found.stage_id,
            "agentId": found.agent_id,
            "summary": found.summary,
            "visibility": found.visibility,
        }
        self._db.execute(
            "INSERT INTO artifacts (id, project_id, run_id, stage_id, agent_id, name, relative_path, mime_type,"
            " file_type, status, visibility, version, size, mtime_ns, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'latest', ?, ?, ?, ?, ?)",
            (artifact["id"], project["id"], run_id, found.stage_id, found.agent_id, found.path.name, relative,
             mime_type_of(found.path), artifact["fileType"], found.visibility, found.version,
             stat.st_size, stat.st_mtime_ns, now_iso()),
        )
        self._events.append(project["id"], {"type": "artifact.created", "artifact": artifact}, run_id)
        self._after_change(project, found, run_id)

    def _touch(self, project: dict, row, found: FoundFile, stat, run_id: str | None, announce: bool) -> None:
        self._db.execute(
            "UPDATE artifacts SET visibility = ?, size = ?, mtime_ns = ?, updated_at = ? WHERE id = ?",
            (found.visibility, stat.st_size, stat.st_mtime_ns, now_iso(), row["id"]),
        )
        payload = {"type": "artifact.updated", "artifactId": row["id"], "status": "latest",
                   "visibility": found.visibility, "summary": found.summary}
        if not announce:
            payload["silent"] = True  # 옛 버전으로 내려간 것뿐 — 카드로 알리지 않는다
        self._events.append(project["id"], payload, run_id)
        if announce:
            self._after_change(project, found, run_id)

    def _after_change(self, project: dict, found: FoundFile, run_id: str | None) -> None:
        """00이 생기면 모드 판정, 최신 05가 생기거나 바뀌면 검증 판정을 알린다."""
        if found.visibility != "primary" or found.number not in ("00", "05"):
            return
        text = found.path.read_text(encoding="utf-8", errors="replace")
        if found.number == "00":
            mode = contract.mode_from_brief(text)
            current = self._db.one("SELECT mode FROM projects WHERE id = ?", (project["id"],))["mode"]
            if mode and mode != current:
                self._db.execute("UPDATE projects SET mode = ?, updated_at = ? WHERE id = ?",
                                 (mode, now_iso(), project["id"]))
                project["mode"] = mode
                self._events.append(project["id"], {"type": "project.mode.decided", "mode": mode}, run_id)
        else:
            verdict = contract.verdict_from_05(text)
            if verdict:
                self._events.append(project["id"], {"type": "validation.verdict", "verdict": verdict[0],
                                                    "firstLine": verdict[1]}, run_id)
