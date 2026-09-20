"""RunManager — 실행 시작 · 중복 방지 · graceful stop · 사용자 응답 후 재개 · 재시작 복구.

한 번에 한 프로젝트의 한 실행만 허용한다(지침서 §22 Phase D). 병렬 실행은 하지 않는다.
실행 상태는 DB에 두고, 메모리에는 지금 돌고 있는 프로세스 하나만 든다 —
백엔드가 다시 켜져도 '응답 대기' 실행은 그대로 이어서 답할 수 있다.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import contract
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
from .scanner import ArtifactSync, Progress, find_new_workspace, scan, track_progress, turn_outcome

log = logging.getLogger(__name__)

ACTIVE_STATUSES = ("running", "awaiting_input", "stopping")
RESUME_PROMPT = "이어서 진행해 주세요."
# 자동 재개했는데 파일·상태가 그대로인 턴이 이만큼 이어지면 복구 불가 오류로 닫는다(끝없이 비용이 나지 않게)
MAX_STALLED_TURNS = 2


# 로이드·요르·본드가 쓰는 CLI(CLAUDE.md §1)
TOOL_COMMANDS = {"claude": "claude", "codex": "codex", "nlm": "nlm"}


class ConflictError(RuntimeError):
    pass


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
            self._projects.require_writable(project)
            active = self.active_run()
            if active:
                if active["project_id"] == project_id:
                    raise ConflictError("이 프로젝트는 이미 실행 중이거나 응답을 기다리고 있습니다.")
                raise ConflictError("다른 프로젝트가 실행 중입니다. 한 번에 하나만 실행할 수 있습니다.")
            first_turn = project["session_id"] is None
            if first_turn and not self._projects.has_undelivered_messages(project_id):
                raise InvalidRequestError("먼저 작업 요청을 입력해 주세요. 요청 문장이 로이드에게 그대로 전달됩니다.")
            result = scan(self._projects.work_root(project), project["workspace_id"], project["mode"])
            if result.finished:
                raise InvalidRequestError("이미 완료된 작업입니다.")

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
                stalled_turns: int = 0) -> None:
        turn = _Turn(run_id=run_id, project_id=project_id, progress=progress, stalled_turns=stalled_turns)
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
        session_id = project["session_id"] or str(uuid.uuid4())
        if not project["session_id"]:
            # 프로세스보다 먼저 저장한다 — 중간에 백엔드가 꺼져도 같은 세션으로 이어 갈 수 있다.
            self._db.execute("UPDATE projects SET session_id = ?, updated_at = ? WHERE id = ?",
                             (session_id, now_iso(), turn.project_id))
        configs = self._run_configs(turn.run_id)
        # 요르·유리·아냐 모델: 로이드가 이 파일을 읽어 호출에 넣는다(루트 .claude/로이드/실행.md §3)
        models_path = self._settings.log_dir / f"{turn.run_id}_models.json"
        models_path.parent.mkdir(parents=True, exist_ok=True)
        models_path.write_text(json.dumps(orchestrator_models(configs), ensure_ascii=False), encoding="utf-8")
        request = TurnRequest(prompt=prompt, session_id=session_id, resume=resume,
                              work_root=self._projects.work_root(project),
                              log_path=self._settings.log_dir / f"{turn.run_id}.jsonl",
                              agent_configs=configs,
                              env={"DOCUMASTER_AGENT_MODELS": str(models_path)})
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
        self._warn_model_mismatch(turn, stage)
        if turn.stop_requested:
            self._finish(turn.run_id, turn.project_id, "stopped", stage)
            return
        if result.exit_code != 0 or result.is_error:
            code = classify_error(result)
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
            self._ask_user(turn, reason, result.result_text)
        else:
            self._continue(turn, scanned, result)

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
        payload = {"completed": {"type": "workflow.completed"},
                   "stopped": {"type": "workflow.stopped", "stageId": stage},
                   "failed": {"type": "workflow.failed", "stageId": stage, "reason": reason}}[status]
        self._events.append(project_id, payload, run_id)

    def _record_turn(self, run_id: str, result: TurnResult) -> None:
        cost = result.extra.get("total_cost_usd")
        self._db.execute(
            "UPDATE runs SET actual_model = COALESCE(?, actual_model),"
            # Claude Code의 total_cost_usd는 같은 세션에서 누적된 값이다.
            " cost_usd = CASE WHEN ? IS NULL THEN cost_usd ELSE MAX(COALESCE(cost_usd, 0), ?) END WHERE id = ?",
            (result.model, cost if isinstance(cost, (int, float)) else None,
             cost if isinstance(cost, (int, float)) else None, run_id),
        )

    def _warn_model_mismatch(self, turn: _Turn, stage: str) -> None:
        """설정과 다른 모델로 부른 호출이 있으면 경고한다(조용히 넘어가지 않는다). 같은 실행에서 한 번씩만."""
        expected = orchestrator_models(self._run_configs(turn.run_id))
        problems = check_model_calls(self._settings.log_dir / f"{turn.run_id}.jsonl", expected)
        seen = self._model_warnings.setdefault(turn.run_id, set())
        for problem in problems:
            if problem in seen:
                continue
            seen.add(problem)
            self._events.append(turn.project_id, {"type": "workflow.warning", "stageId": stage,
                                                  "message": f"모델 설정과 다른 호출: {problem}"}, turn.run_id)

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

    def shutdown(self) -> None:
        """백엔드를 끌 때 로이드 프로세스를 남겨 두지 않는다(보이지 않는 곳에서 비용이 나지 않게)."""
        with self._lock:
            turn = self._turn
        if turn and turn.process and turn.process.is_alive():
            turn.stop_requested = True
            turn.process.terminate()
        for thread in self._threads:
            thread.join(timeout=10)
