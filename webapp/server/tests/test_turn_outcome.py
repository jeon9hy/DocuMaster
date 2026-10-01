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
