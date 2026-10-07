"""RunManager — 실행 시작 · 중복 방지 · 실행 예약(대기열) · graceful stop · 사용자 응답 후 재개 · 재시작 복구.

한 번에 한 프로젝트의 한 실행만 허용한다(지침서 §22 Phase D). 병렬 실행은 하지 않는다 — 토큰 한도를 두 실행이 나눠 쓰면
둘 다 느려지고 중간에 막힌다. 대신 다른 프로젝트가 돌고 있으면 **예약**해 두고, 앞 실행이 완료·오류로 끝나면 예약 순서대로
시작한다. 중지(사용자·백엔드 재시작)로 끝나면 예약은 기다린다 — 사용자가 멈춘 뒤 다른 실행이 저절로 시작되지 않게.
실행 상태는 DB에 두고, 메모리에는 지금 돌고 있는 프로세스 하나만 든다 —
백엔드가 다시 켜져도 '응답 대기' 실행은 그대로 이어서 답할 수 있다.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import contract, git_sync
from .agent_settings import AgentSettingsService, check_model_calls, load_snapshot, orchestrator_models
from .config import Settings
from .db import Database, now_iso
from .events import EventStore
from .files import FileStore
from .orchestrator import (
    OrchestratorAdapter,
    ProcessTurn,
    TurnRequest,
    TurnResult,
    classify_error,
    describe_error,
)
from .projects import InvalidRequestError, NotFoundError, ProjectService
from .scanner import (ArtifactSync, Progress, final_dirs, find_new_workspace, previous_final_version, scan,
                      track_progress, turn_outcome)
from .yor_feed import YorLogFollower

log = logging.getLogger(__name__)

ACTIVE_STATUSES = ("running", "awaiting_input", "stopping")
RESUME_PROMPT = "이어서 진행해 주세요."
# 자동 재개했는데 파일·상태가 그대로인 턴이 이만큼 이어지면 복구 불가 오류로 닫는다(끝없이 비용이 나지 않게)
MAX_STALLED_TURNS = 2
# 명령 안전 검사(서버 쪽) 일시 장애로 턴이 끝나면 이만큼 기다렸다가 같은 세션으로 한 번만 다시 이어 간다
PERMISSION_RETRY_SECONDS = 60


# 로이드·요르·본드가 쓰는 CLI(CLAUDE.md §1)
TOOL_COMMANDS = {"claude": "claude", "codex": "codex", "nlm": "nlm"}

# 상태.md를 쓰는 루트 도구 — 이 코드와 같은 저장소의 규칙(작업 루트가 임시 폴더여도 같은 도구를 쓴다)
_STAGE_TOOL = Path(__file__).resolve().parents[3] / ".claude" / "tools" / "stage.py"
# 첨삭 요청 길이 상한(로이드에게 그대로 넘긴다)
MAX_REVISE_CHARS = 4000
# 첨삭 실행이 시작될 때·멈출 때 상태.md에 쓰는 줄(루트 skills/doc-revise §1)
REVISE_STATUS = "진행 중 첨삭"
REVISE_PROMPT = ("완료된 문서의 첨삭 요청이다. `.claude/skills/doc-revise`를 따른다 — 상태 줄은 웹앱이 이미 "
                 f"「{REVISE_STATUS}」으로 두었다. 요르·유리는 부르지 않는다. 대상 밖의 최종 PDF는 건드리지 않는다."
                 "\n\n[첨삭 대상] {target}\n\n[첨삭 요청]\n")
# 중지·오류(사용량 한도 등)로 끊긴 첨삭을 같은 세션으로 이어 갈 때의 문장
REVISE_RESUME_PROMPT = ("중단됐던 첨삭(`.claude/skills/doc-revise`)을 이어서 한다 — 상태 줄은 웹앱이 다시 "
                        f"「{REVISE_STATUS}」으로 두었다. 중단 때 하위 에이전트(아냐)의 작업은 끝나지 않았을 수 있다. "
                        "작업 폴더의 최신 07 새 버전과 revise 기록을 보고 남은 지시 항목부터 잇는다. "
                        "대상 밖의 최종 PDF는 건드리지 않는다.\n\n[첨삭 대상] {target}")
_REVISE_REQUEST_LINE = "첨삭 요청 · "


class ConflictError(RuntimeError):
    pass


class BusyError(ConflictError):
    """다른 프로젝트가 실행 중 — 화면이 「끝나면 시작」 예약을 제안한다."""


def _with_queued(text: str, queued: list[str]) -> str:
    """기다리는 동안 보낸 지시를 다음 턴 문장 뒤에 그대로 붙인다(지침서 §17)."""
    if not queued:
        return text
    return text + "\n\n추가 지시:\n" + "\n".join(f"- {item}" for item in queued)


@dataclass
class _Turn:
    run_id: str
    project_id: str
    process: ProcessTurn | None = None
    progress: Progress = field(default_factory=Progress)
    stop_requested: bool = False
    stop_baseline: frozenset[str] = frozenset()
    started_at: float = field(default_factory=time.time)
    stalled_turns: int = 0  # 진행 없이 끝난 연속 자동 재개 턴 수
    permission_retries: int = 0  # 명령 안전 검사 장애로 다시 이어 간 횟수
    fingerprint: tuple = ()
    persisted_worker: tuple[str, str] | None = None


class RunManager:
    def __init__(self, settings: Settings, db: Database, events: EventStore, files: FileStore,
                 projects: ProjectService, adapter: OrchestratorAdapter, agent_settings: AgentSettingsService):
        self._settings = settings
        self._db = db
        self._events = events
        self._files = files
        self._projects = projects
        self._adapter = adapter
        self._agent_settings = agent_settings
        self._model_warnings: dict[str, set[str]] = {}
        # 요르(Codex) 로그를 프로젝트마다 따라 읽는다 — 로이드 턴이 바뀌어도 이어서 읽어야 해서 턴 밖에 둔다
        self._yor_feeds: dict[str, YorLogFollower] = {}
        self._sync = ArtifactSync(db, events, files)
        self._lock = threading.RLock()
        self._turn: _Turn | None = None
        self._threads: list[threading.Thread] = []

    # --- 조회 --------------------------------------------------------------------

    def active_run(self, project_id: str | None = None) -> dict | None:
        sql = f"SELECT * FROM runs WHERE status IN {ACTIVE_STATUSES}"
        rows = self._db.query(sql + (" AND project_id = ?" if project_id else ""),
                              (project_id,) if project_id else ())
        return dict(rows[0]) if rows else None

    def status(self) -> dict:
        run = self.active_run()
        return {"orchestrator": self._adapter.name, "missingTools": self._adapter.missing_tools(),
                # 홈 「시스템 상태」: PATH에 있는지만 본다(로그인·한도는 확인하지 않는다 — LLM을 부르지 않는다)
                "tools": {name: shutil.which(command) is not None for name, command in TOOL_COMMANDS.items()},
                "activeRun": {"id": run["id"], "projectId": run["project_id"], "status": run["status"]} if run else None}

    # --- 시작 --------------------------------------------------------------------

    def start(self, project_id: str) -> str:
        with self._lock:
            project = self._projects.get(project_id)
            self._check_startable(project)
            active = self.active_run()
            if active:
                if active["project_id"] == project_id:
                    raise ConflictError("이 프로젝트는 이미 실행 중이거나 응답을 기다리고 있습니다.")
                raise BusyError("다른 프로젝트가 실행 중입니다. 한 번에 하나만 실행할 수 있습니다.")
            self._drop_from_queue(project_id)
            result = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
            if result.finished:  # _check_startable이 끊긴 첨삭이 있을 때만 통과시킨다
                return self._resume_revise(project, self._paused_revise(project_id))
            first_turn = project["session_id"] is None

            run_id = f"run_{uuid.uuid4().hex[:12]}"
            self._db.execute(
                "INSERT INTO runs (id, project_id, status, started_at, agent_config_json)"
                " VALUES (?, ?, 'running', ?, ?)",
                (run_id, project_id, now_iso(), self._agent_settings.snapshot_json()),
            )
            self._events.append(project_id, {"type": "workflow.started"}, run_id)
            prompt = self._compose_prompt(project, first_turn, self._projects.take_undelivered_messages(project_id))
            self._launch(run_id, project_id, prompt, resume=not first_turn, progress=Progress.resume_from(result))
            return run_id

    def _check_startable(self, project: dict) -> None:
        self._projects.require_writable(project)
        if (project["session_id"] is None and not self._projects.has_undelivered_messages(project["id"])
                and not self._paused_revise(project["id"])):
            raise InvalidRequestError("먼저 작업 요청을 입력해 주세요. 요청 문장이 로이드에게 그대로 전달됩니다.")
        result = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
        if result.finished and not self._paused_revise(project["id"]):
            raise InvalidRequestError("이미 완료된 작업입니다.")

    # --- 첨삭 --------------------------------------------------------------------

    def revise(self, project_id: str, text: str, target: str | None = None) -> str:
        """완료된 문서(DOC 최종본)를 첨삭한다 — 원래 작업 세션과 따로 새 로이드 세션을 연다(긴 조사 맥락을 다시 싣지 않게).

        요르·유리 없이 로이드·아냐만 쓴다(skills/doc-revise). 예약은 받지 않는다 — 다른 실행이 돌고 있으면 거절한다.
        target은 고칠 최종 PDF의 파일 이름이다(최종본이 여러 부일 때). 없으면 <ID>.pdf, 그것도 없으면 하나뿐인 PDF.
        """
        text = text.strip()
        if not text:
            raise InvalidRequestError("첨삭 요청이 비어 있습니다.")
        if len(text) > MAX_REVISE_CHARS:
            raise InvalidRequestError(f"첨삭 요청은 {MAX_REVISE_CHARS}자 이하로 써 주세요.")
        with self._lock:
            project = self._projects.get(project_id)
            document = self._revise_target(project, target)
            active = self.active_run()
            if active:
                if active["project_id"] == project_id:
                    raise ConflictError("이 프로젝트는 이미 실행 중이거나 응답을 기다리고 있습니다.")
                raise BusyError("다른 프로젝트가 실행 중입니다. 끝난 뒤 첨삭해 주세요.")
            work_root = self._projects.work_root(project)
            self._set_state_line(work_root, project["workspace_id"], REVISE_STATUS, "doc-revise")
            result = scan(work_root, project["workspace_id"], project["mode"])

            run_id = f"run_{uuid.uuid4().hex[:12]}"
            self._db.execute(
                "INSERT INTO runs (id, project_id, status, started_at, agent_config_json, kind, session_id, revise_target)"
                " VALUES (?, ?, 'running', ?, ?, 'revise', ?, ?)",
                (run_id, project_id, now_iso(), self._agent_settings.snapshot_json(), str(uuid.uuid4()), document.name),
            )
            self._events.append(project_id, {"type": "user.message",
                                             "text": f"{_REVISE_REQUEST_LINE}{document.name}\n" + text}, run_id)
            self._events.append(project_id, {"type": "workflow.started"}, run_id)
            prompt = REVISE_PROMPT.format(target=document.relative_to(work_root).as_posix()) + text
            self._launch(run_id, project_id, prompt, resume=False, progress=Progress.resume_from(result))
            return run_id

    def _paused_revise(self, project_id: str) -> dict | None:
        """이 프로젝트의 마지막 실행이 중지·오류로 끝난 첨삭이면 그 실행. 새 첨삭·실행이 뒤에 있으면 없다."""
        row = self._db.one("SELECT * FROM runs WHERE project_id = ? ORDER BY started_at DESC, rowid DESC LIMIT 1",
                           (project_id,))
        if row is None or row["kind"] != "revise" or row["status"] not in ("stopped", "failed"):
            return None
        return dict(row)

    def _paused_revise_target(self, run: dict) -> str | None:
        """끊긴 첨삭이 고치던 PDF 이름. 열이 생기기 전 실행은 시작 때 남긴 「첨삭 요청 · <PDF>」 줄에서 읽는다."""
        if run.get("revise_target"):
            return run["revise_target"]
        row = self._db.one("SELECT payload_json FROM events WHERE run_id = ? AND type = 'user.message'"
                           " ORDER BY seq LIMIT 1", (run["id"],))
        text = json.loads(row["payload_json"]).get("text", "") if row else ""
        first = text.splitlines()[0] if text else ""
        if not first.startswith(_REVISE_REQUEST_LINE):
            return None
        return first[len(_REVISE_REQUEST_LINE):].strip() or None

    def _resume_revise(self, project: dict, paused: dict | None) -> str:
        """끊긴 첨삭을 같은 로이드 세션(--resume)으로 잇는다 — 첨삭 요청·반영 판정을 다시 하지 않게."""
        if paused is None:
            raise InvalidRequestError("이미 완료된 작업입니다.")
        project_id = project["id"]
        document = self._revise_target(project, self._paused_revise_target(paused))
        work_root = self._projects.work_root(project)
        self._set_state_line(work_root, project["workspace_id"], REVISE_STATUS, "doc-revise",
                             note=f"첨삭 이어서 — 중단된 실행 {paused['id']}")
        result = scan(work_root, project["workspace_id"], project["mode"])
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        self._db.execute(
            "INSERT INTO runs (id, project_id, status, started_at, agent_config_json, kind, session_id, revise_target)"
            " VALUES (?, ?, 'running', ?, ?, 'revise', ?, ?)",
            (run_id, project_id, now_iso(), self._agent_settings.snapshot_json(), paused["session_id"], document.name),
        )
        self._events.append(project_id, {"type": "workflow.started"}, run_id)
        prompt = _with_queued(REVISE_RESUME_PROMPT.format(target=document.relative_to(work_root).as_posix()),
                              self._projects.take_undelivered_messages(project_id))
        self._launch(run_id, project_id, prompt, resume=True, progress=Progress.resume_from(result))
        return run_id

    def _revise_target(self, project: dict, target: str | None) -> Path:
        """완료된 문서 모드일 때 최종/<유형>/<ID>/의 최종 PDF(이전판 제외) 중 고칠 것 하나(발표는 아냐 대상이 아니다)."""
        workspace_id = project["workspace_id"]
        if not workspace_id:
            raise InvalidRequestError("아직 작업 폴더가 없는 프로젝트입니다.")
        work_root = self._projects.work_root(project)
        if not scan(work_root, workspace_id, project["mode"]).finished:
            raise InvalidRequestError("최종본까지 끝난 문서만 첨삭할 수 있습니다.")
        # 본문(<ID>.pdf)이 앞에 — 대상을 고르지 않은 옛 요청은 본문을 고친다
        documents = sorted(
            (path for folder in final_dirs(work_root, workspace_id) if folder.parent.name != "발표"
             for path in folder.glob("*.pdf") if path.is_file() and previous_final_version(path) is None),
            key=lambda path: (path.stem != workspace_id, path.name))
        if project["mode"] == "presentation" or not documents:
            raise InvalidRequestError("첨삭은 문서 최종본(PDF)이 있는 문서 프로젝트만 할 수 있습니다.")
        if not target:
            if len(documents) > 1 and documents[0].stem != workspace_id:
                raise InvalidRequestError("최종본이 여러 개입니다. 첨삭할 PDF를 골라 주세요.")
            return documents[0]
        chosen = next((path for path in documents if path.name == target), None)
        if chosen is None:
            raise InvalidRequestError(f"첨삭할 수 있는 최종본이 아닙니다: {target}")
        return chosen

    def _set_state_line(self, work_root: Path, workspace_id: str, status: str, next_step: str, note: str = "") -> None:
        """상태.md는 루트 규칙대로 stage.py로만 쓴다(CLAUDE.md §6)."""
        command = [sys.executable, str(_STAGE_TOOL), "set",
                   "--id", workspace_id, "--status", status, "--next", next_step]
        if note:
            command += ["--log", note]
        done = subprocess.run(command, cwd=work_root, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False,
                              env={**os.environ, "DOCUMASTER_WORK_ROOT": str(work_root), "PYTHONIOENCODING": "utf-8"})
        if done.returncode != 0:
            raise InvalidRequestError("상태 파일을 고치지 못했습니다: " + (done.stderr or done.stdout).strip()[-300:])

    def _run_row(self, run_id: str) -> dict:
        row = self._db.one("SELECT * FROM runs WHERE id = ?", (run_id,))
        return dict(row) if row else {}

    # --- 예약(대기열) ----------------------------------------------------------------

    def enqueue(self, project_id: str) -> dict:
        """앞 실행이 끝나면 시작하도록 예약한다. 비어 있으면 바로 시작한다."""
        with self._lock:
            project = self._projects.get(project_id)
            self._check_startable(project)
            active = self.active_run()
            if not active:
                return {"started": True, "runId": self.start(project_id)}
            if active["project_id"] == project_id:
                raise ConflictError("이 프로젝트는 이미 실행 중이거나 응답을 기다리고 있습니다.")
            if self._db.one("SELECT 1 FROM run_queue WHERE project_id = ?", (project_id,)):
                raise ConflictError("이미 예약되어 있습니다.")
            self._db.execute("INSERT INTO run_queue (project_id, queued_at) VALUES (?, ?)", (project_id, now_iso()))
            self._events.append(project_id, {"type": "workflow.queued"})
            return {"started": False, "position": self._queue_position(project_id)}

    def cancel_queued(self, project_id: str, reason: str | None = None) -> None:
        with self._lock:
            if not self._drop_from_queue(project_id, reason):
                raise ConflictError("예약된 실행이 없습니다.")

    def _drop_from_queue(self, project_id: str, reason: str | None = None) -> bool:
        if not self._db.one("SELECT 1 FROM run_queue WHERE project_id = ?", (project_id,)):
            return False
        self._db.execute("DELETE FROM run_queue WHERE project_id = ?", (project_id,))
        payload = {"type": "workflow.queue.cancelled"}
        if reason:
            payload["reason"] = reason
        self._events.append(project_id, payload)
        return True

    def _queue_position(self, project_id: str) -> int:
        rows = self._db.query("SELECT project_id FROM run_queue ORDER BY queued_at")
        return next((index + 1 for index, row in enumerate(rows) if row["project_id"] == project_id), 0)

    def _start_next_queued(self) -> None:
        """앞 실행이 끝났다 — 예약 순서대로 하나를 시작한다. 시작할 수 없는 예약은 이유와 함께 지운다."""
        with self._lock:
            if self.active_run():
                return
            for row in self._db.query("SELECT project_id FROM run_queue ORDER BY queued_at"):
                project_id = row["project_id"]
                try:
                    self.start(project_id)
                    return
                except (NotFoundError, InvalidRequestError, ConflictError) as error:
                    if not self._drop_from_queue(project_id, f"예약한 실행을 시작하지 못했습니다: {error}"):
                        self._db.execute("DELETE FROM run_queue WHERE project_id = ?", (project_id,))

    def _compose_prompt(self, project: dict, first_turn: bool, messages: list[str]) -> str:
        """사용자가 CLI에 칠 문장과 같게 만든다: 요청 원문 + (정했다면) 형식 + 참고자료 경로.

        지시를 요약하거나 절차를 덧붙이지 않는다 — 절차는 CLAUDE.md·.claude/가 정한다.
        """
        parts = ["\n\n".join(messages) if messages else RESUME_PROMPT]
        if first_turn and project["mode"] != "auto":
            parts.append("형식: " + ("문서(DOCUMENT)" if project["mode"] == "document" else "발표(PRESENTATION)"))
        references = self._projects.active_references(project["id"])
        if first_turn and references:
            lines = [f"- {ref['relative_path']}" if ref["relative_path"] else f"- {ref['url']}"
                     for ref in references]
            parts.append("참고자료:\n" + "\n".join(lines))
        return "\n\n".join(parts)

    # --- 사용자 응답 ---------------------------------------------------------------

    def respond(self, project_id: str, prompt_id: str, answer: str) -> None:
        answer = answer.strip()
        if not answer:
            raise InvalidRequestError("응답이 비어 있습니다.")
        with self._lock:
            row = self._db.one("SELECT * FROM pending_inputs WHERE id = ? AND project_id = ?", (prompt_id, project_id))
            if row is None:
                raise NotFoundError("확인 요청을 찾을 수 없습니다.")
            if row["status"] != "open":
                raise ConflictError("이미 응답했거나 취소된 요청입니다.")
            run = self.active_run(project_id)
            if not run or run["status"] != "awaiting_input":
                raise ConflictError("응답을 기다리는 실행이 없습니다.")
            self._db.execute("UPDATE pending_inputs SET status = 'answered', answer = ?, answered_at = ? WHERE id = ?",
                             (answer, now_iso(), prompt_id))
            self._set_run(run["id"], status="running")
            self._events.append(project_id, {"type": "user.input.resolved", "promptId": prompt_id, "answer": answer},
                                run["id"])
            # 응답과 함께, 기다리는 동안 보낸 지시도 다음 턴에 넘긴다(지침서 §17).
            prompt = _with_queued(answer, self._projects.take_undelivered_messages(project_id))
            project = self._projects.get(project_id)
            result = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
            progress = Progress.continuing(result, project["mode"])
            self._launch(run["id"], project_id, prompt, resume=True, progress=progress)

    # --- 중지 --------------------------------------------------------------------

    def request_stop(self, project_id: str) -> None:
        """현재 단계가 끝나면 멈춘다. 응답 대기 중이면 바로 멈춘다(돌고 있는 프로세스가 없다)."""
        with self._lock:
            run = self.active_run(project_id)
            if not run:
                raise ConflictError("실행 중이 아닙니다.")
            if run["status"] == "awaiting_input":
                self._db.execute("UPDATE pending_inputs SET status = 'cancelled' WHERE run_id = ? AND status = 'open'",
                                 (run["id"],))
                self._finish(run["id"], project_id, "stopped", self._current_stage(project_id, run))
                return
            if run["status"] == "stopping":
                return
            self._set_run(run["id"], status="stopping", stop_requested=1)
            if self._turn and self._turn.run_id == run["id"]:
                self._turn.stop_requested = True
                self._turn.stop_baseline = self._turn.progress.completed
            self._events.append(project_id, {"type": "workflow.stop.requested"}, run["id"])

    # --- 턴 실행 ------------------------------------------------------------------

    def _launch(self, run_id: str, project_id: str, prompt: str, resume: bool, progress: Progress,
                stalled_turns: int = 0, permission_retries: int = 0) -> None:
        turn = _Turn(run_id=run_id, project_id=project_id, progress=progress, stalled_turns=stalled_turns,
                     permission_retries=permission_retries)
        with self._lock:
            self._turn = turn
        thread = threading.Thread(target=self._run_turn, args=(turn, prompt, resume), daemon=True,
                                  name=f"run-{run_id}")
        self._threads = [t for t in self._threads if t.is_alive()] + [thread]
        thread.start()

    def _run_turn(self, turn: _Turn, prompt: str, resume: bool) -> None:
        try:
            self._drive(turn, prompt, resume)
        except Exception:  # 감시 스레드가 조용히 죽지 않게 — 실행을 오류로 닫는다
            log.exception("실행 감시 중 예외")
            self._finish(turn.run_id, turn.project_id, "failed", self._stage_of(turn),
                         reason=describe_error("agent_process_error"), error_code="agent_process_error")
        finally:
            with self._lock:
                if self._turn is turn:
                    self._turn = None

    def _drive(self, turn: _Turn, prompt: str, resume: bool) -> None:
        project = self._projects.get(turn.project_id)
        missing = self._adapter.missing_tools()
        if missing:
            self._finish(turn.run_id, turn.project_id, "failed", self._stage_of(turn),
                         reason=describe_error("orchestrator_unavailable") + f" (없음: {', '.join(missing)})",
                         error_code="orchestrator_unavailable")
            return
        run = self._run_row(turn.run_id)
        revising = run.get("kind") == "revise"
        session_id = run["session_id"] if revising else (project["session_id"] or str(uuid.uuid4()))
        if not revising and not project["session_id"]:
            # 프로세스보다 먼저 저장한다 — 중간에 백엔드가 꺼져도 같은 세션으로 이어 갈 수 있다.
            self._db.execute("UPDATE projects SET session_id = ?, updated_at = ? WHERE id = ?",
                             (session_id, now_iso(), turn.project_id))
        configs = self._run_configs(turn.run_id)
        models = orchestrator_models(configs)
        # 요르·유리·아냐 모델: 로이드가 이 파일을 읽어 호출에 넣는다(루트 .claude/로이드/실행.md §3)
        models_path = self._settings.log_dir / f"{turn.run_id}_models.json"
        models_path.parent.mkdir(parents=True, exist_ok=True)
        models_path.write_text(json.dumps(models, ensure_ascii=False), encoding="utf-8")
        runtime_prompt = prompt
        if self._settings.orchestrator == "claude":
            yor = models["yor"]
            runtime_prompt = (
                "[웹앱 실행 계약 — 이 블록은 현재 실행에만 적용]\n"
                f"- 실행 ID: {turn.run_id}\n"
                f"- 현재 웹 프로젝트: {project['display_name']} ({project['id']})\n"
                f"- 이 프로젝트에 배정된 작업 ID: {project['workspace_id']}\n"
                f"- 작업 경로는 작업/{project['workspace_id']}, 최종 경로는 최종/<유형>/{project['workspace_id']}"
                "(CLAUDE.md §4 — PPT는 최종/발표)만 사용한다.\n"
                "- 다른 작업 ID의 상태·파일·최종본을 탐색하거나 이어받거나 완료 근거로 삼지 않는다.\n"
                f"- DOCUMASTER_AGENT_MODELS가 가리키는 현재 실행 스냅샷: {models_path}\n"
                f"- 요르 호출값(yor.py가 위 스냅샷에서 읽는다): model={yor['model']}, reasoning={yor['effort']}\n"
                "- 경로 이름이 임시·스모크처럼 보여도 이 파일을 무시하거나 기본값으로 대체하지 않는다.\n"
                f"- 요르는 `python .claude/tools/yor.py <종류> --id {project['workspace_id']}`로만 부른다. "
                "codex를 직접 부르거나 사용법을 조회하지 않는다.\n"
                "- yor.py는 포그라운드로 기다린다. 백그라운드로 넘어가면 턴을 끝내지 말고 `yor.py wait`을 반복한다.\n\n"
                "[사용자 요청]\n" + prompt
            )
        request = TurnRequest(prompt=runtime_prompt, session_id=session_id, resume=resume,
                              work_root=self._projects.work_root(project),
                              log_path=self._settings.log_dir / f"{turn.run_id}.jsonl",
                              workspace_id=project["workspace_id"],
                              agent_configs=configs,
                              env={"DOCUMASTER_AGENT_MODELS": str(models_path)}, revise=revising)
        try:
            turn.process = ProcessTurn(
                self._adapter.build_command(request), request,
                on_activity=lambda payload: self._events.append(turn.project_id, payload, turn.run_id),
            )
        except OSError as error:
            self._finish(turn.run_id, turn.project_id, "failed", self._stage_of(turn),
                         reason=describe_error("orchestrator_unavailable") + f" ({error})",
                         error_code="orchestrator_unavailable")
            return
        self._set_run(turn.run_id, pid=turn.process.pid)
        turn.fingerprint = scan(request.work_root, project["workspace_id"], project["mode"]).fingerprint()

        while turn.process.is_alive():
            self._tick(turn)
            if turn.stop_requested and turn.progress.completed - turn.stop_baseline:
                turn.process.terminate()  # 요청 뒤 단계 하나가 끝났다 — 다음 단계로 넘어가기 전에 멈춘다
                break
            time.sleep(self._settings.poll_seconds)
        result = turn.process.wait()
        self._tick(turn)
        self._record_turn(turn.run_id, result)
        self._conclude(turn, result)

    def _tick(self, turn: _Turn) -> None:
        """작업 폴더를 다시 보고 바뀐 것만 이벤트로 낸다."""
        project = self._projects.get(turn.project_id)
        if not project["workspace_id"]:
            workspace_id = self._discover_workspace(project, turn.started_at)
            if workspace_id:
                project["workspace_id"] = workspace_id
        result = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
        self._sync.sync(project, result, turn.run_id)
        # ArtifactSync가 00의 모드를 판정하면 전달받은 project도 갱신한다.
        turn.progress, payloads = track_progress(turn.progress, result, project["mode"])
        for payload in payloads:
            self._events.append(turn.project_id, payload, turn.run_id)
        if project["workspace_id"]:
            feed = self._yor_feeds.setdefault(turn.project_id, YorLogFollower())
            work_dir = self._projects.work_root(project) / "작업" / project["workspace_id"]
            for payload in feed.poll(work_dir):
                self._events.append(turn.project_id, payload, turn.run_id)
        if turn.progress.worker and turn.progress.worker != turn.persisted_worker:
            self._set_run(turn.run_id, current_stage=turn.progress.worker[0], current_agent=turn.progress.worker[1])
            turn.persisted_worker = turn.progress.worker

    def _discover_workspace(self, project: dict, since: float) -> str | None:
        claimed = {row["workspace_id"] for row in self._db.query(
            "SELECT workspace_id FROM projects WHERE work_root = ? AND workspace_id IS NOT NULL",
            (project["work_root"],))}
        workspace_id = find_new_workspace(self._projects.work_root(project), since, claimed)
        if workspace_id:
            self._db.execute("UPDATE projects SET workspace_id = ?, description = ?, updated_at = ? WHERE id = ?",
                             (workspace_id, f"작업/{workspace_id}", now_iso(), project["id"]))
        return workspace_id

    def _conclude(self, turn: _Turn, result: TurnResult) -> None:
        project = self._projects.get(turn.project_id)
        stage = self._stage_of(turn)
        model_problems = self._model_mismatches(turn, stage)
        if model_problems:
            self._finish(turn.run_id, turn.project_id, "failed", stage,
                         reason="모델 실행값이 홈페이지 설정과 달라 중단했습니다. " + " ".join(model_problems),
                         error_code="model_config_mismatch")
            return
        code = classify_error(result) if result.exit_code != 0 or result.is_error else None
        # 중지 요청 뒤라도 한도에 걸려 끝났으면 그 이유(풀리는 시각)를 알린다 — 「중지」로만 보이지 않게
        if turn.stop_requested and code != "usage_limit":
            self._finish(turn.run_id, turn.project_id, "stopped", stage)
            return
        if code:
            if code == "permission_check_unavailable" and turn.permission_retries < 1:
                self._retry_after_permission_outage(turn, stage)
                return
            self._finish(turn.run_id, turn.project_id, "failed", stage,
                         reason=describe_error(code, result), error_code=code)
            return
        scanned = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
        outcome, reason = turn_outcome(scanned)
        if outcome == "completed":
            if result.result_text and not turn.process.already_streamed(result.result_text):
                self._events.append(turn.project_id, {"type": "agent.message", "agentId": "loid",
                                                      "text": result.result_text}, turn.run_id)
            self._finish(turn.run_id, turn.project_id, "completed", stage)
        elif outcome == "needs_input":
            already_asked_before_workspace = not scanned.workspace_exists and self._db.one(
                "SELECT 1 FROM pending_inputs WHERE run_id = ? AND title = ?",
                (turn.run_id, "로이드의 확인 요청 · 작업 시작 전"),
            )
            if already_asked_before_workspace:
                self._finish(
                    turn.run_id, turn.project_id, "failed", stage,
                    reason="로이드가 사용자 응답 뒤에도 배정된 작업 폴더를 만들지 않아 실행을 닫았습니다. 새 요청으로 다시 실행하세요.",
                    error_code="orchestrator_stalled",
                )
            else:
                self._ask_user(turn, reason, result.result_text)
        else:
            self._continue(turn, scanned, result)

    def _retry_after_permission_outage(self, turn: _Turn, stage: str) -> None:
        """서버 쪽 일시 장애 — 모델·명령 탓이 아니다. 잠깐 기다렸다가 같은 세션으로 한 번만 이어 간다."""
        self._events.append(turn.project_id, {
            "type": "workflow.warning", "stageId": stage,
            "message": (f"Claude Code의 명령 안전 검사(Anthropic 서버 쪽)가 응답하지 않아 턴이 멈췄습니다. 일시 장애라 "
                        f"{PERMISSION_RETRY_SECONDS}초 뒤 같은 세션으로 한 번 이어서 합니다."),
        }, turn.run_id)
        deadline = time.monotonic() + PERMISSION_RETRY_SECONDS
        while time.monotonic() < deadline:
            if turn.stop_requested:
                self._finish(turn.run_id, turn.project_id, "stopped", stage)
                return
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        prompt = _with_queued(RESUME_PROMPT, self._projects.take_undelivered_messages(turn.project_id))
        self._launch(turn.run_id, turn.project_id, prompt, resume=True, progress=turn.progress,
                     stalled_turns=turn.stalled_turns, permission_retries=turn.permission_retries + 1)

    def _continue(self, turn: _Turn, scanned, result: TurnResult) -> None:
        """사람이 개입할 상태가 아닌데 턴이 끝났다 — 같은 세션을 고정 문구로 이어 간다."""
        stalled = turn.stalled_turns + 1 if scanned.fingerprint() == turn.fingerprint else 0
        if stalled >= MAX_STALLED_TURNS:
            reason = "로이드가 작업 파일을 진행하지 않은 채 턴을 반복해 끝냈습니다. 마지막 보고를 확인한 뒤 다시 실행하세요."
            if result.result_text:
                reason += f" (마지막 보고: {result.result_text.strip().splitlines()[-1][:200]})"
            self._finish(turn.run_id, turn.project_id, "failed", self._stage_of(turn),
                         reason=reason, error_code="orchestrator_stalled")
            return
        if result.result_text and not turn.process.already_streamed(result.result_text):
            self._events.append(turn.project_id, {"type": "agent.message", "agentId": "loid",
                                                  "text": result.result_text}, turn.run_id)
        prompt = _with_queued(RESUME_PROMPT, self._projects.take_undelivered_messages(turn.project_id))
        self._launch(turn.run_id, turn.project_id, prompt, resume=True, progress=turn.progress,
                     stalled_turns=stalled)

    def _ask_user(self, turn: _Turn, title: str, message: str) -> None:
        """구조화된 상태(상태.md·05 판정·작업 시작 전)가 사람의 개입을 요구할 때만 부른다."""
        prompt_id = f"prompt_{uuid.uuid4().hex[:12]}"
        request = {"promptId": prompt_id, "title": title[:80],
                   "message": message.strip() or "로이드가 다음 지시를 기다립니다.",
                   "choices": [], "allowFreeText": True, "stageId": self._stage_of(turn)}
        self._db.execute(
            "INSERT INTO pending_inputs (id, project_id, run_id, title, message, choices_json, allow_free_text,"
            " status, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, 'open', ?)",
            (prompt_id, turn.project_id, turn.run_id, request["title"], request["message"],
             json.dumps(request["choices"], ensure_ascii=False), now_iso()),
        )
        self._set_run(turn.run_id, status="awaiting_input")
        self._events.append(turn.project_id, {"type": "user.input.required", "request": request}, turn.run_id)

    # --- 마무리·복구 ----------------------------------------------------------------

    def _finish(self, run_id: str, project_id: str, status: str, stage: str,
                reason: str = "", error_code: str | None = None) -> None:
        self._set_run(run_id, status=status, finished_at=now_iso(), error_code=error_code)
        self._model_warnings.pop(run_id, None)  # 끝난 실행의 경고 중복 거르기 — 백엔드가 오래 떠 있어도 쌓이지 않게
        run = self._run_row(run_id)
        paused_revise = status != "completed" and run.get("kind") == "revise"
        if paused_revise:
            self._restore_after_revise(run_id, project_id)
        if status == "completed":
            payload = {"type": "workflow.completed"}
            try:
                payload["summary"] = self._summary(run_id, project_id)
            except Exception:  # 요약을 못 만들어도 완료는 알린다
                log.exception("완료 요약을 만들지 못했습니다")
        else:
            payload = {"stopped": {"type": "workflow.stopped", "stageId": stage},
                       "failed": {"type": "workflow.failed", "stageId": stage, "reason": reason}}[status]
            if paused_revise:
                payload["revise"] = True  # 첨삭이 멈춘 것 — 원래 작업의 단계 상태는 그대로다
        self._events.append(project_id, payload, run_id)
        if paused_revise:
            self._announce_paused_revise(run, project_id)
        if status == "completed":
            self._sync_to_git(run_id, project_id)
        if status in ("completed", "failed"):
            # 이 스레드는 끝난 실행의 감시 스레드다 — 다음 실행은 자기 스레드에서 돈다(_launch)
            self._start_next_queued()

    def _restore_after_revise(self, run_id: str, project_id: str) -> None:
        """첨삭이 중지·오류로 끝났다 — 최종본은 교체 전이므로 상태를 다시 「완료」로 돌린다(원래 작업이 미완료로 보이지 않게)."""
        project = self._projects.get(project_id)
        work_root = self._projects.work_root(project)
        if scan(work_root, project["workspace_id"], project["mode"]).finished:
            return  # 로이드가 이미 교체하고 닫았다
        try:
            self._set_state_line(work_root, project["workspace_id"], "완료",
                                 "없음 — 첨삭 중단(웹앱 「첨삭 이어서」로 같은 세션 재개), 최종본은 이전 그대로",
                                 note=f"첨삭 실행 {run_id} 중단 — 최종본 교체 전")
        except InvalidRequestError:
            log.exception("첨삭 중단 뒤 상태를 되돌리지 못했습니다: %s", run_id)
            self._events.append(project_id, {
                "type": "workflow.warning", "stageId": "finalReview",
                "message": "첨삭을 멈춘 뒤 상태 파일을 「완료」로 되돌리지 못했습니다. 최종본은 이전 그대로입니다.",
            }, run_id)

    def _announce_paused_revise(self, run: dict, project_id: str) -> None:
        """화면이 「첨삭 이어서」 버튼을 켜도록 알린다. 이어 가기는 start()가 같은 세션으로 한다."""
        target = self._paused_revise_target(run)
        self._events.append(project_id, {"type": "revise.paused", "target": target or ""}, run["id"])

    def _sync_to_git(self, run_id: str, project_id: str) -> None:
        """완료된 프로젝트의 작업·최종 파일과 manifest만 커밋·푸시한다. 실패는 대화에 경고로만 남긴다."""
        project = self._projects.get(project_id)
        root, workspace_id = self._projects.work_root(project), project.get("workspace_id")
        if not workspace_id or not git_sync.enabled(self._settings, root):
            return

        def sync() -> None:
            try:
                git_sync.commit_paths(self._settings.repo_root, git_sync.project_paths(root, workspace_id),
                                      f"docs(final): {workspace_id} 완료", push=True)
            except Exception as error:
                log.exception("완료본을 Git에 반영하지 못했습니다: %s", workspace_id)
                self._events.append(project_id, {
                    "type": "workflow.warning", "stageId": "finalReview",
                    "message": f"완료본을 GitHub에 올리지 못했습니다. 파일은 로컬에 있습니다. ({str(error)[:200]})",
                }, run_id)

        threading.Thread(target=sync, name=f"git-sync-{project_id}", daemon=True).start()

    def _summary(self, run_id: str, project_id: str) -> dict:
        """완료 카드에 모을 값 — 이미 DB·파일에 있는 것만 읽는다(모델을 부르지 않는다)."""
        run = self._db.one("SELECT * FROM runs WHERE id = ?", (run_id,))
        summary: dict = {"costUsd": run["cost_usd"] if run else None}
        if run and run["started_at"] and run["finished_at"]:
            started, finished = (datetime.fromisoformat(value.replace("Z", "+00:00"))
                                 for value in (run["started_at"], run["finished_at"]))
            summary["durationSeconds"] = max(0, round((finished - started).total_seconds()))
        configs = self._run_configs(run_id)
        summary["models"] = {agent: config.get("modelId") for agent, config in configs.items()
                             if isinstance(config, dict) and config.get("modelId")}
        finals = self._db.query(
            # 최종/<유형>/<ID>/의 파일만 finalReview·primary다(output/ 렌더 결과·이전판은 internal)
            "SELECT id FROM artifacts WHERE project_id = ? AND stage_id = 'finalReview' AND visibility = 'primary'"
            " AND file_type = 'pdf' ORDER BY name", (project_id,))
        # 최종본이 여러 부면(본문 + 연습문제 등) 모두 싣는다. finalArtifactId는 예전 이벤트와 같은 모양을 지키는 첫 파일
        summary["finalArtifactIds"] = [row["id"] for row in finals]
        summary["finalArtifactId"] = finals[0]["id"] if finals else None
        project = self._projects.get(project_id)
        scanned = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
        latest_05 = next((found.path for found in scanned.files
                          if found.number == "05" and found.visibility == "primary"), None)
        if latest_05:
            text = latest_05.read_text(encoding="utf-8", errors="replace")
            verdict = contract.verdict_from_05(text)
            counts = contract.claim_counts_from_05(text)
            summary.update(verdict=verdict[0] if verdict else None,
                           removeCount=counts.get("remove"), cautionCount=counts.get("caution"))
        return summary

    def _record_turn(self, run_id: str, result: TurnResult) -> None:
        cost = result.extra.get("total_cost_usd")
        self._db.execute(
            "UPDATE runs SET actual_model = COALESCE(?, actual_model),"
            # Claude Code의 total_cost_usd는 같은 세션에서 누적된 값이다.
            " cost_usd = CASE WHEN ? IS NULL THEN cost_usd ELSE MAX(COALESCE(cost_usd, 0), ?) END WHERE id = ?",
            (result.model, cost if isinstance(cost, (int, float)) else None,
             cost if isinstance(cost, (int, float)) else None, run_id),
        )

    def _model_mismatches(self, turn: _Turn, stage: str) -> list[str]:
        """설정과 다른 호출을 이벤트로 알리고 반환한다. 호출자는 실행을 실패로 닫는다."""
        expected = orchestrator_models(self._run_configs(turn.run_id))
        problems = check_model_calls(self._settings.log_dir / f"{turn.run_id}.jsonl", expected)
        seen = self._model_warnings.setdefault(turn.run_id, set())
        for problem in problems:
            if problem in seen:
                continue
            seen.add(problem)
            self._events.append(turn.project_id, {"type": "workflow.warning", "stageId": stage,
                                                  "message": f"모델 설정과 다른 호출: {problem}"}, turn.run_id)
        return problems

    def _run_configs(self, run_id: str) -> dict:
        """이 실행이 시작할 때 고정한 설정. 응답 뒤 재개 턴도 같은 값을 쓴다."""
        row = self._db.one("SELECT agent_config_json FROM runs WHERE id = ?", (run_id,))
        return load_snapshot(row["agent_config_json"] if row else None)

    def _set_run(self, run_id: str, **fields) -> None:
        columns = ", ".join(f"{name} = ?" for name in fields)
        self._db.execute(f"UPDATE runs SET {columns} WHERE id = ?", (*fields.values(), run_id))

    def _stage_of(self, turn: _Turn) -> str:
        if turn.progress.worker:
            return turn.progress.worker[0]
        return next((stage for stage in contract.STAGES if stage not in turn.progress.completed), "finalReview")

    def _current_stage(self, project_id: str, run: dict) -> str:
        return run["current_stage"] or "requirements"

    def recover_on_startup(self) -> None:
        """꺼지기 전에 돌던 실행은 프로세스가 없으므로 '중지됨'으로 닫는다. 응답 대기는 그대로 둔다."""
        for run in self._db.query("SELECT * FROM runs WHERE status IN ('running', 'stopping')"):
            stage = run["current_stage"] or "requirements"
            self._events.append(run["project_id"], {
                "type": "workflow.warning", "stageId": stage,
                "message": "백엔드가 다시 시작되어 진행 중이던 실행이 중단되었습니다. 「워크플로우 실행」으로 이어서 할 수 있습니다.",
            }, run["id"])
            self._finish(run["id"], run["project_id"], "stopped", stage)
        # 이 기능 전에 끊긴 첨삭도 화면에서 이어 갈 수 있게 알림을 한 번 채운다
        for project in self._db.query("SELECT DISTINCT r.project_id FROM runs r JOIN projects p ON p.id = r.project_id"
                                      " WHERE r.kind = 'revise' AND p.deleted_at IS NULL"):
            paused = self._paused_revise(project["project_id"])
            if paused and not self._db.one("SELECT 1 FROM events WHERE run_id = ? AND type = 'revise.paused'",
                                           (paused["id"],)):
                self._announce_paused_revise(paused, project["project_id"])

    def shutdown(self) -> None:
        """백엔드를 끌 때 로이드 프로세스를 남겨 두지 않는다(보이지 않는 곳에서 비용이 나지 않게)."""
        with self._lock:
            turn = self._turn
        if turn and turn.process and turn.process.is_alive():
            turn.stop_requested = True
            turn.process.terminate()
        for thread in self._threads:
            thread.join(timeout=10)
