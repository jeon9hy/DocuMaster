"""상태 갱신 도구(.claude/tools/stage.py) — 양식대로 쓰는지, 자리표시자가 남으면 완료를 막는지."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).parents[3] / ".claude" / "tools" / "stage.py"
ID = "테스트_20260928"
TODAY = "2026-09-28"


@pytest.fixture(scope="module")
def stage():
    spec = importlib.util.spec_from_file_location("stage_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(root: Path, name: str) -> str:
    return (root / "작업" / ID / name).read_text(encoding="utf-8")


def test_init_done_log_and_finish(tmp_path, stage):
    run = lambda *args: stage.run(list(args), root=tmp_path, today=TODAY)  # noqa: E731
    run("init", "--id", ID, "--topic", "테스트 주제", "--mode", "DOCUMENT")
    state = read(tmp_path, "상태.md")
    assert state.splitlines()[0] == f"# {ID} — 테스트 주제 · 모드: DOCUMENT"
    assert "요르 기획 세션 ID: 해당 없음(DOC)" in state
    with pytest.raises(stage.Stop):
        run("init", "--id", ID, "--topic", "x", "--mode", "DOCUMENT")  # 덮어쓰지 않는다

    run("done", "00·01", "--id", ID, "--output", "workspace/00,01", "--note", "로이드 직접",
        "--status", "진행 중 02 조사", "--next", "요르 조사 02", "--log", "로이드: 00·01 작성, 게이트 통과")
    (tmp_path / "작업" / ID / "_yor_sessions.json").write_text(json.dumps({"research": "sess-1"}), encoding="utf-8")
    run("done", "02", "--id", ID, "--output", "workspace/02", "--note", "gpt/medium",
        "--status", "진행 중 03 검증질문", "--next", "유리 03")
    run("done", "00·01", "--id", ID, "--note", "다시 확인")  # 같은 행을 고친다(새 행 아님)
    run("set", "--id", ID, "--session", "유리 에이전트=abc123", "--open", "검증 라운드 1/1 · REMOVE 1")

    lines = read(tmp_path, "상태.md").splitlines()
    assert lines[1] == "상태: 진행 중 03 검증질문" and lines[2] == "다음에 할 일: 유리 03"
    rows = [line for line in lines if line.startswith("| ") and "단계" not in line]
    assert rows == ["| 00·01 | workspace/00,01 | 완료 | 다시 확인 |", "| 02 | workspace/02 | 완료 | gpt/medium |"]
    session = next(line for line in lines if line.startswith("## 세션"))
    assert "요르 조사 세션 ID: sess-1" in session and "유리 에이전트: abc123 ·" in session
    assert next(line for line in lines if line.startswith("## 열린 것")).endswith("검증 라운드 1/1 · REMOVE 1")
    assert read(tmp_path, "기록.md") == f"# 기록 — {ID}\n- {TODAY} 로이드: 00·01 작성, 게이트 통과\n"

    # 아냐 에이전트가 아직 자리표시자 — 완료로 바꾸지 않는다
    with pytest.raises(stage.Stop, match="자리표시자"):
        run("finish", "--id", ID, "--final", f"최종/{ID}/{ID}.pdf")
    assert read(tmp_path, "상태.md").splitlines()[1] == "상태: 진행 중 03 검증질문"

    run("set", "--id", ID, "--session", "아냐 에이전트=def456", "--session", "실제 모델=gpt(확인)")
    # 이관 전 — 최종 파일이 없으면 완료로 바꾸지 않는다
    with pytest.raises(stage.Stop, match="--final 파일이 없다"):
        run("finish", "--id", ID, "--final", f"최종/분석/{ID}/{ID}.pdf")
    final = tmp_path / "최종" / "분석" / ID / f"{ID}.pdf"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"%PDF")
    run("finish", "--id", ID, "--final", f"최종/분석/{ID}/{ID}.pdf", "--manifest", f"{ID}.pdf (DOCUMENT · 4쪽)")
    lines = read(tmp_path, "상태.md").splitlines()
    assert lines[1] == "상태: 완료" and lines[2] == f"다음에 할 일: 없음 — 최종/분석/{ID}/{ID}.pdf"
    manifest = (tmp_path / "최종" / "_manifest.md").read_text(encoding="utf-8")
    assert manifest == f"- {TODAY} · [분석] `{ID}` · {ID}.pdf (DOCUMENT · 4쪽)\n"


def test_manifest_kind_reads_only_the_type_folder(stage):
    """최종/<유형>/<ID>/<파일>에서만 유형을 읽는다 — 옛 평면 경로의 ID를 유형으로 읽지 않는다."""
    assert stage.manifest_kind(f"최종/분석/{ID}/{ID}.pdf") == "분석"
    assert stage.manifest_kind(f"최종/발표/{ID}/{ID}_슬라이드.pdf") == "발표"
    assert stage.manifest_kind(f"최종/{ID}/{ID}.pdf") == ""
    assert stage.manifest_kind(f"작업/{ID}/output/{ID}.pdf") == ""


def test_reads_an_existing_real_layout(tmp_path, stage):
    """실제 실행이 쓴 상태.md(헤더가 `## 진행` 줄에 붙은 표)도 그대로 고친다."""
    base = tmp_path / "작업" / ID
    base.mkdir(parents=True)
    (base / "상태.md").write_text(
        f"# {ID} — 주제 · 모드: DOCUMENT\n상태: 진행 중 07\n다음에 할 일: doc-finish\n\n"
        "## 진행      | 단계 | 산출물 | 상태 | 비고 |\n|---|---|---|---|\n"
        "| 07 DOC | workspace/07 | 진행 중 | 아냐 |\n"
        "## 세션      유리 에이전트: a1 · 아냐 에이전트: (실행 후 기록)\n## 열린 것   없음\n", encoding="utf-8")
    stage.run(["done", "07", "--id", ID, "--note", "아냐 opus", "--session", "아냐 에이전트=b2"], root=tmp_path)
    text = (base / "상태.md").read_text(encoding="utf-8")
    assert "| 07 DOC | workspace/07 | 완료 | 아냐 opus |" in text
    assert "## 세션      유리 에이전트: a1 · 아냐 에이전트: b2\n" in text


def test_finish_with_kind_copies_rendered_pdf(tmp_path, stage):
    """DOC 이관: 유형만 주면 output/<ID>.pdf를 최종/<유형>/<ID>/로 옮기고 완료·manifest까지 쓴다."""
    run = lambda *args: stage.run(list(args), root=tmp_path, today=TODAY)  # noqa: E731
    run("init", "--id", ID, "--topic", "주제", "--mode", "DOCUMENT")
    run("set", "--id", ID, "--session", "요르 조사 세션 ID=s1", "--session", "유리 에이전트=a1",
        "--session", "아냐 에이전트=b2")
    with pytest.raises(stage.Stop, match="렌더된 PDF가 없다"):
        run("finish", "--id", ID, "--kind", "분석", "--manifest", "x")
    with pytest.raises(SystemExit):  # 유형 이름은 정해진 일곱 개뿐(가운뎃점 없이)
        run("finish", "--id", ID, "--kind", "분석·해설")
    output = tmp_path / "작업" / ID / "output"
    output.mkdir()
    (output / f"{ID}.pdf").write_bytes(b"%PDF-1.7")
    assert run("finish", "--id", ID, "--kind", "분석", "--manifest", f"{ID}.pdf (3쪽)") == f"stage finish: {ID} · 완료"
    assert (tmp_path / "최종" / "분석" / ID / f"{ID}.pdf").read_bytes() == b"%PDF-1.7"
    assert read(tmp_path, "상태.md").splitlines()[2] == f"다음에 할 일: 없음 — 최종/분석/{ID}/{ID}.pdf"
    assert "[분석] `" in (tmp_path / "최종" / "_manifest.md").read_text(encoding="utf-8")


def test_log_for_unknown_job_stops_cleanly(tmp_path, stage):
    with pytest.raises(stage.Stop, match="작업 ID를 확인"):
        stage.run(["log", "--id", "없는작업", "기록"], root=tmp_path, today=TODAY)
    assert not (tmp_path / "작업").exists()
