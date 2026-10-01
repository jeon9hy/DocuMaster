"""턴이 끝난 뒤 판단(scanner.turn_outcome)과 오류 분류(orchestrator.classify_error)."""

from __future__ import annotations

from app.orchestrator import TurnResult, classify_error
from app.scanner import ScanResult, turn_outcome


def _scanned(numbers: set[str], verdict: str | None = None) -> ScanResult:
    return ScanResult(numbers=numbers, workspace_exists=True, status="진행 중", verdict=verdict)


def test_blocked_verdict_asks_before_next_stage() -> None:
    assert turn_outcome(_scanned({"00", "01", "02", "03", "04", "05"}, "blocked"))[0] == "needs_input"


def test_blocked_verdict_does_not_ask_again_after_document_07() -> None:
    """사용자가 blocked를 풀어 준 뒤 DOC 07을 썼다 — 같은 05로 다시 묻지 않는다."""
    assert turn_outcome(_scanned({"00", "01", "02", "03", "04", "05", "07"}, "blocked"))[0] == "continue"


def test_blocked_verdict_does_not_ask_again_after_presentation_06() -> None:
    assert turn_outcome(_scanned({"00", "01", "02", "03", "04", "05", "06"}, "blocked"))[0] == "continue"


def test_usage_limit_needs_whole_number() -> None:
    assert classify_error(TurnResult(exit_code=1, stderr_tail="HTTP 429 Too Many Requests")) == "usage_limit"
    assert classify_error(TurnResult(exit_code=1, stderr_tail="file 4290.md not found")) == "agent_process_error"


def test_tool_modules_check_is_remembered_only_when_ready(monkeypatch) -> None:
    """렌더 도구 모듈 확인 — 있으면 기억하고, 없으면 다음에 다시 본다."""
    import subprocess

    from app import orchestrator

    calls = []

    def fake_run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1 if len(calls) == 1 else 0)

    monkeypatch.setattr(orchestrator, "_TOOL_MODULES_READY", False)
    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    assert orchestrator.python_tool_modules_ready() is False
    assert orchestrator.python_tool_modules_ready() is True
    assert orchestrator.python_tool_modules_ready() is True
    assert len(calls) == 2


def test_new_pipeline_tools_have_activity_labels() -> None:
    from app.orchestrator import _command_label

    assert _command_label('python .claude/tools/render_doc.py "회사_20261001" --pages 3') == "문서 검사·렌더링"
    assert _command_label("python .claude/tools/source_check.py X S01=16.5") == "원문 대조"
