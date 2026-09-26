"""Thin Adapter — 기존 DocuMaster 오케스트레이터(로이드 세션)를 프로세스로 띄우고 결과만 받는다.

하는 일: 실행 요청 전달 · 종료 코드/결과 수집 · 중지 요청 전달 · 오류 분류.
하지 않는 일: 프롬프트 재작성 · 단계 통합 · 모델 변경 · Context 축약 · 검증 생략 · Gate 완화.

한 "턴" = 프로세스 하나. 로이드가 사용자에게 물을 때 턴이 끝나고, 답은 같은 세션을 --resume해서 넘긴다.
프롬프트는 stdin으로 넘긴다(명령줄에 사용자 문자열을 붙이지 않는다 — shell 해석 없음).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .config import Settings

_FAKE_SCRIPT = Path(__file__).with_name("fake_orchestrator.py")
_STDERR_TAIL = 4000
log = logging.getLogger(__name__)
_AGENT_NAMES = {"로이드": "loid", "요르": "yor", "유리": "yuri", "아냐": "anya", "본드": "bond"}


def _agent_in(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return next((agent for name, agent in _AGENT_NAMES.items() if name in value), None)


def _tool_label(name: str, data: dict) -> str | None:
    """도구 입력 본문·명령·검색어는 노출하지 않고 활동 종류와 파일명만 보여 준다."""
    if name in {"Read", "Write", "Edit", "MultiEdit"}:
        path = data.get("file_path") or data.get("path")
        filename = str(path).replace("\\", "/").rsplit("/", 1)[-1] if path else ""
        verb = {"Read": "파일 읽기", "Write": "파일 작성", "Edit": "파일 수정", "MultiEdit": "파일 수정"}[name]
        return f"{verb} · {filename[:100]}" if filename else verb
    if name == "WebFetch":
        host = urlparse(str(data.get("url") or "")).hostname
        return f"웹 자료 열기 · {host}" if host else "웹 자료 열기"
    return {
        "WebSearch": "웹 검색", "ToolSearch": "도구 검색",
        "Agent": "하위 에이전트 작업 요청", "SendMessage": "에이전트에게 메시지 전달",
        "SubagentHandback": "검토 결과 전달", "Skill": "작업 지침 확인",
    }.get(name)


class StreamActivity:
    """실제 stream-json에서 공개 가능한 발언과 도구 활동만 추출한다."""

    def __init__(self):
        self._subagent_by_call: dict[str, str | None] = {}
        self._subagent_by_id: dict[str, str] = {}
        self.emitted_texts: set[str] = set()

    def read(self, message: dict) -> list[dict]:
        if message.get("type") == "user":
            self._read_agent_launch(message)
            return []
        if message.get("type") != "assistant":
            return []
        envelope = message.get("message")
        content = envelope.get("content") if isinstance(envelope, dict) else None
        if not isinstance(content, list):
            return []
        parent = message.get("parent_tool_use_id")
        agent_id = self._subagent_by_call.get(parent) if parent else "loid"
        if not agent_id:
            return []  # 역할을 확인할 수 없는 하위 실행은 로이드의 말로 꾸미지 않는다.
        events = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                value = str(block.get("text") or "").strip()
                if value:
                    if agent_id == "loid":
                        self.emitted_texts.add(value)
                    events.append({"type": "agent.message", "agentId": agent_id, "text": value})
            elif block.get("type") == "tool_use":
                name = str(block.get("name") or "")
                data = block.get("input") if isinstance(block.get("input"), dict) else {}
                if name == "Agent" and isinstance(block.get("id"), str):
                    self._subagent_by_call[block["id"]] = _agent_in(data.get("description"))
                if name == "SendMessage":
                    target = self._subagent_by_id.get(str(data.get("recipient") or data.get("to") or ""))
                    speech = data.get("content") or data.get("message")
                    if target and isinstance(speech, str) and speech.strip():
                        events.append({"type": "agent.message", "agentId": agent_id,
                                       "toAgentId": target, "text": speech.strip()})
                        continue
                label = _tool_label(name, data)
                if label:
                    target = _agent_in(data.get("description")) if name == "Agent" else None
                    if target:
                        label += f" · {next(key for key, value in _AGENT_NAMES.items() if value == target)}"
                    events.append({"type": "agent.activity", "agentId": agent_id, "label": label})
        return events

    def _read_agent_launch(self, message: dict) -> None:
        envelope = message.get("message")
        blocks = envelope.get("content") if isinstance(envelope, dict) else None
        if not isinstance(blocks, list):
            return
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            agent = self._subagent_by_call.get(block.get("tool_use_id"))
            if not agent:
                continue
            content = block.get("content")
            texts = [part.get("text", "") for part in content if isinstance(part, dict)] if isinstance(content, list) else []
            for value in texts:
                found = re.search(r"\bagentId:\s*([A-Za-z0-9]+)", str(value))
                if found:
                    self._subagent_by_id[found.group(1)] = agent


@dataclass(frozen=True)
class TurnRequest:
    prompt: str
    session_id: str
    resume: bool
    work_root: Path
    log_path: Path
    workspace_id: str | None = None
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
        if request.workspace_id:
            command += ["--workspace-id", request.workspace_id]
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
    """프로세스 하나를 띄우고 stdout을 기록하며 공개 가능한 활동을 즉시 전달한다."""

    def __init__(self, command: list[str], request: TurnRequest,
                 on_activity: Callable[[dict], None] | None = None):
        request.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._request = request
        self._result = TurnResult(exit_code=None)
        self._stderr: list[str] = []
        self._terminated = False
        self._on_activity = on_activity
        self._stream_activity = StreamActivity()
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

    def already_streamed(self, text: str) -> bool:
        return text.strip() in self._stream_activity.emitted_texts

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
        if self._on_activity:
            try:
                for activity in self._stream_activity.read(message):
                    self._on_activity(activity)
            except Exception:
                # UI 이벤트 오류가 오케스트레이터의 stdout 수집을 멈추면 안 된다.
                log.exception("실시간 대화 이벤트 전달 실패")
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
