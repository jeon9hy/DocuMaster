"""문서 게이트의 0건 판정과 완료 상태 기록 검사를 확인한다."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[3] / ".claude" / "tools" / "gate_check.py"
SPEC = importlib.util.spec_from_file_location("gate_check", MODULE_PATH)
assert SPEC and SPEC.loader
gate_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate_check)


def setup_function() -> None:
    gate_check.results.clear()


def test_zero_remove_and_caution_are_ok_without_empty_tables() -> None:
    verified = (
        "# Verified Research Pack\n"
        "- APPROVED 7 · CORRECTED 0 · REMOVE 0 · CAUTION 0\n"
        "--- 헤더 끝 ---\n"
    )

    gate_check.check_remove("본문", verified)
    gate_check.check_caution("본문", verified, strict=False)

    assert gate_check.results == [
        ("OK", "REMOVE", "05 헤더에 REMOVE 0건으로 명시"),
        ("OK", "CAUTION", "05 헤더에 CAUTION 0건으로 명시"),
    ]


def test_completed_state_rejects_session_placeholders() -> None:
    gate_check.check_state_bookkeeping(
        "## 세션 yor=(실행 후 기록) · 유리 에이전트=(미실행)\n"
    )

    assert gate_check.results[0][0:2] == ("FAIL", "상태 기록")


def test_completed_state_accepts_actual_ids_and_not_applicable_roles() -> None:
    gate_check.check_state_bookkeeping(
        "## 세션 yor=019abc · 유리 에이전트=agent-42 · 아냐 에이전트=해당 없음(PPT)\n"
    )

    assert gate_check.results == [("OK", "상태 기록", "세션·에이전트 자리표시자 없음")]
