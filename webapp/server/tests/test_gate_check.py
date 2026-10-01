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


def test_empty_table_row_is_not_an_item() -> None:
    """0건을 `| 없음 | — | — |` 한 행으로 적은 05 — REMOVE 1건으로 세지 않는다."""
    verified = (
        "- APPROVED 3 · CORRECTED 0 · REMOVE 0 · CAUTION 0\n--- 헤더 끝 ---\n## 1. 판정 요약\n"
        "### REMOVE\n| 항목(근거 ID) | 삭제 사유 | 영향 |\n| --- | --- | --- |\n| 없음 | — | — |\n"
        "### CAUTION\n| 항목(근거 ID) | 쓸 수 있는 범위 | 한계 문장 |\n| --- | --- | --- |\n| 없음 | — | — |\n"
    )

    gate_check.check_remove("본문", verified)
    gate_check.check_caution("본문", verified, strict=False)
    gate_check.check_corrected(verified)

    assert gate_check.results == [
        ("OK", "REMOVE", "05 헤더에 REMOVE 0건으로 명시"),
        ("OK", "CAUTION", "05 헤더에 CAUTION 0건으로 명시"),
    ]


def _section5(rows: str) -> str:
    return "## 2. 검증된 사실\n- 값이다 (S01)\n## 5. 출처\n" + rows


def test_05_sources_dates_with_02_are_not_file_references() -> None:
    gate_check.check_05(_section5("- S01 | 참고 통계 | 통계청 | 2026-02-04 | https://example.com\n"))

    assert not [r for r in gate_check.results if r[0] == "FAIL"]


def test_05_sources_pointing_to_02_fail() -> None:
    gate_check.check_05(_section5("- S01 | 02 §G 참조 | 통계청 | 2026 | https://example.com\n"))

    assert ("FAIL", "05 §5", "02·04를 가리킨다 — 05는 혼자 읽혀야 한다") in gate_check.results


def test_bare_evidence_id_in_body_fails() -> None:
    """`[S03]` 밖의 근거 ID는 렌더되면 독자에게 보인다 — 위첨자 인용·출처 블록·메타데이터는 통과."""
    body = ("---\ntitle: S01 제목처럼 보여도 메타데이터\n---\n"
            "보험료율은 9.5%다.[S01] 같은 근거의 두 문장이다.[S01][S02]\n"
            "<!-- S05는 주석 -->\n"
            "| 구분 | 값 |\n| --- | --- |\n| 2026 | 4.75% |\n"
            "자료: S01 부칙 제4조·S02 요율 기준\n")
    gate_check.check_bare_ids(body)
    fails = [r for r in gate_check.results if r[0] == "FAIL"]
    assert len(fails) == 1 and "자료: S01 부칙" in fails[0][2]
