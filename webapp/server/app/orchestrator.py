"""Thin Adapter — 기존 DocuMaster 오케스트레이터(로이드 세션)를 프로세스로 띄우고 결과만 받는다.

하는 일: 실행 요청 전달 · 종료 코드/결과 수집 · 중지 요청 전달 · 오류 분류.
하지 않는 일: 프롬프트 재작성 · 단계 통합 · 모델 변경 · Context 축약 · 검증 생략 · Gate 완화.

한 "턴" = 프로세스 하나. 로이드가 사용자에게 물을 때 턴이 끝나고, 답은 같은 세션을 --resume해서 넘긴다.
프롬프트는 stdin으로 넘긴다(명령줄에 사용자 문자열을 붙이지 않는다 — shell 해석 없음).
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings

_FAKE_SCRIPT = Path(__file__).with_name("fake_orchestrator.py")
_STDERR_TAIL = 4000


@dataclass(frozen=True)
class TurnRequest:
    prompt: str
    session_id: str
    resume: bool
    work_root: Path
    log_path: Path
    """실행 시작 때 고정한 에이전트 설정(agent_settings). 없으면 기본 배치."""
    agent_configs: dict = field(default_factory=dict)
    """프로세스에 더할 환경변수(DOCUMASTER_AGENT_MODELS 등)"""
    env: dict = field(default_factory=dict)


@dataclass
class TurnResult:
    exit_code: int | None
    result_text: str = ""
    is_error: bool = False
    session_id: str | None = None
    model: str | None = None
    stderr_tail: str = ""
    terminated: bool = False
    extra: dict = field(default_factory=dict)


class OrchestratorAdapter:
    """명령을 만드는 부분만 구현마다 다르다. 실행·감시·종료는 ProcessTurn이 공통으로 한다."""

    name = "base"

    def build_command(self, request: TurnRequest) -> list[str]:
        raise NotImplementedError

    def missing_tools(self) -> list[str]:
        return []


class FakeOrchestratorAdapter(OrchestratorAdapter):
    """비용 없는 가짜 로이드. 샌드박스에 계약 파일을 쓰고 claude와 같은 stream-json을 낸다."""

    name = "fake"

    def __init__(self, settings: Settings):
        self._step = settings.fake_step_seconds

    def build_command(self, request: TurnRequest) -> list[str]:
        command = [sys.executable, str(_FAKE_SCRIPT), "--work-root", str(request.work_root),
                   "--session-id", request.session_id, "--step-seconds", str(self._step)]
        return command + (["--resume"] if request.resume else [])


class ClaudeCodeOrchestratorAdapter(OrchestratorAdapter):
    """저장소 루트에서 `claude -p`로 로이드 세션을 연다. CLAUDE.md·.claude/는 Claude Code가 그대로 읽는다.

    --model/--effort는 Owner가 설정 화면에서 로이드 값을 바꿨을 때만 넘긴다(기본은 사용자의 Claude Code 설정).
    --fallback-model은 넘기지 않는다 — 한도·오류 때 다른 모델로 조용히 바꾸지 않는다.
    옵션은 `claude --help`(2.1.278)에서 확인한 것만 쓴다.
    """

    name = "claude"

    def __init__(self, settings: Settings):
        self._permission_mode = settings.claude_permission_mode

    def build_command(self, request: TurnRequest) -> list[str]:
        executable = shutil.which("claude") or "claude"
        session = ["--resume", request.session_id] if request.resume else ["--session-id", request.session_id]
        return [executable, "-p", "--output-format", "stream-json", "--verbose",
                "--permission-mode", self._permission_mode, *session, *loid_model_flags(request.agent_configs)]

    def missing_tools(self) -> list[str]:
        # 로이드가 부르는 도구(CLAUDE.md §1). 없으면 실행 전에 알린다.
        tools = {"claude": "claude", "codex": "codex", "python": "python"}
        return [label for label, command in tools.items() if not shutil.which(command)]


def loid_model_flags(agent_configs: dict) -> list[str]:
    """로이드 설정 → claude CLI 옵션. 기본값(claude-code-default · None)이면 아무것도 넘기지 않는다."""
    config = agent_configs.get("loid") or {}
    flags = []
    if config.get("modelId") and config["modelId"] != "claude-code-default":
        flags += ["--model", config["modelId"]]
    if config.get("reasoningLevel"):
        flags += ["--effort", config["reasoningLevel"]]
    return flags


def create_adapter(settings: Settings) -> OrchestratorAdapter:
    if settings.orchestrator == "claude":
        return ClaudeCodeOrchestratorAdapter(settings)
    if settings.orchestrator == "fake":
        return FakeOrchestratorAdapter(settings)
    raise ValueError(f"알 수 없는 오케스트레이터: {settings.orchestrator}")


class ProcessTurn:
    """프로세스 하나를 띄우고 stdout(stream-json)에서 init·result만 읽는다.

    나머지 줄(도구 호출·중간 출력)은 화면에 보내지 않고 로그 파일에만 남긴다(지침서 §15).
    """

    def __init__(self, command: list[str], request: TurnRequest):
        request.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._request = request
        self._result = TurnResult(exit_code=None)
        self._stderr: list[str] = []
        self._terminated = False
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        self._process = subprocess.Popen(
            command,
            cwd=request.work_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **request.env, "PYTHONIOENCODING": "utf-8"},
            creationflags=flags,
            start_new_session=os.name != "nt",
        )
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()
        assert self._process.stdin is not None
        try:
            self._process.stdin.write(request.prompt.encode("utf-8"))
            self._process.stdin.close()
        except OSError:
            pass  # 프로세스가 곧바로 끝난 경우 — 종료 코드로 알린다

    @property
    def pid(self) -> int:
        return self._process.pid

    def is_alive(self) -> bool:
        return self._process.poll() is None

    def wait(self) -> TurnResult:
        self._result.exit_code = self._process.wait()
        self._stdout_thread.join(timeout=5)
        self._stderr_thread.join(timeout=5)
        self._result.stderr_tail = "".join(self._stderr)[-_STDERR_TAIL:]
        self._result.terminated = self._terminated
        return self._result

    def terminate(self) -> None:
        """프로세스 트리를 끝낸다(로이드가 띄운 codex·python 포함)."""
        if not self.is_alive():
            return
        self._terminated = True
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(self._process.pid), "/T", "/F"],
                           capture_output=True, check=False)
        else:
            os.killpg(self._process.pid, signal.SIGTERM)

    def _read_stdout(self) -> None:
        assert self._process.stdout is not None
        with self._request.log_path.open("a", encoding="utf-8") as log:
            for raw in self._process.stdout:
                line = raw.decode("utf-8", errors="replace")
                log.write(line)
                log.flush()
                self._handle_line(line)

    def _read_stderr(self) -> None:
        assert self._process.stderr is not None
        for raw in self._process.stderr:
            self._stderr.append(raw.decode("utf-8", errors="replace"))
            if len(self._stderr) > 200:
                del self._stderr[:100]

    def _handle_line(self, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(message, dict):
            return
        if message.get("type") == "system" and message.get("subtype") == "init":
            self._result.session_id = message.get("session_id")
            self._result.model = message.get("model")
        elif message.get("type") == "result":
            self._result.result_text = str(message.get("result") or "")
            self._result.is_error = bool(message.get("is_error"))
            self._result.session_id = message.get("session_id") or self._result.session_id
            self._result.extra = {key: message.get(key) for key in ("total_cost_usd", "num_turns", "duration_ms")
                                  if key in message}


# --- 오류 분류(지침서 §19) ----------------------------------------------------------

_ERROR_RULES = (
    ("claude_auth_required", ("/login", "not logged in", "invalid api key", "authentication_error", "please run `claude")),
    ("codex_auth_required", ("codex login", "codex: not logged")),
    ("notebooklm_login_required", ("nlm login",)),
    ("usage_limit", ("usage limit", "rate limit", "429")),
)

ERROR_MESSAGES = {
    "orchestrator_unavailable": "오케스트레이터를 실행하지 못했습니다. claude CLI 설치와 PATH를 확인하세요.",
    "claude_auth_required": "Claude Code 로그인이 필요합니다. 터미널에서 `claude`를 실행해 로그인한 뒤 다시 시도하세요.",
    "codex_auth_required": "Codex 로그인이 필요합니다. 터미널에서 `codex login`을 완료한 뒤 다시 시도하세요.",
    "notebooklm_login_required": "NotebookLM 로그인이 필요합니다. 터미널에서 `nlm login`을 완료한 뒤 다시 시도하세요.",
    "usage_limit": "모델 사용량 한도에 걸렸습니다. 한도가 풀린 뒤 「워크플로우 실행」으로 이어서 하세요(모델은 바꾸지 않습니다).",
    "agent_process_error": "에이전트 프로세스가 오류로 끝났습니다.",
}


def classify_error(result: TurnResult) -> str:
    haystack = f"{result.result_text}\n{result.stderr_tail}".lower()
    for code, needles in _ERROR_RULES:
        if any(needle in haystack for needle in needles):
            return code
    return "agent_process_error"


def describe_error(code: str, result: TurnResult | None = None) -> str:
    message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["agent_process_error"])
    if code == "agent_process_error" and result:
        detail = (result.result_text or result.stderr_tail).strip().splitlines()
        if detail:
            message += f" ({detail[-1][:200]})"
    return message
