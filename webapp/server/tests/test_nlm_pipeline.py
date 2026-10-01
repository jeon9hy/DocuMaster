"""NotebookLM 파이프라인(.claude/tools/nlm_pipeline.py) — nlm을 부르지 않는 부분만."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[3] / ".claude" / "tools" / "nlm_pipeline.py"


@pytest.fixture
def nlm(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("nlm_pipeline", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def test_focus_prompt_keeps_grounding_when_instruction_is_long(nlm):
    prompt = nlm.focus_prompt("지시" * 8000, "추가 지시")
    assert len(prompt) <= nlm.FOCUS_LIMIT
    assert prompt.endswith(nlm.GROUNDING) and "추가 지시" in prompt


def test_upload_guard_refuses_intermediate_files(nlm, tmp_path):
    for name in ("00_user_brief.md", "05_verified_research_pack.md", "06_detailed_plan.md"):
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        with pytest.raises(SystemExit, match="업로드 거부"):
            nlm.guard_source(path)


def test_promote_replaces_its_manifest_line(nlm, tmp_path):
    job_id = "발표_20261001"
    output = tmp_path / "작업" / job_id / "output"
    workspace = tmp_path / "작업" / job_id / "workspace"
    output.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (output / f"{job_id}_slides.pdf").write_bytes(b"%PDF")
    (workspace / "07_notebooklm_presentation_pack.md").write_text("# Presentation Pack\n", encoding="utf-8")
    (output / "_nlm_run.json").write_text(json.dumps({
        "pack": f"작업/{job_id}/workspace/07_notebooklm_presentation_pack.md",
        "artifacts": {"slides": {"files": {".pdf": f"작업/{job_id}/output/{job_id}_slides.pdf"}}},
        "inspection": {"slides.pdf": {"ok": True, "novel_numbers": []}},
    }), encoding="utf-8")
    manifest = tmp_path / "최종" / "_manifest.md"
    manifest.parent.mkdir()
    manifest.write_text("- 2026-09-30 · [분석] `다른작업` · a.pdf\n", encoding="utf-8")

    for _ in range(2):
        assert nlm.cmd_promote(argparse.Namespace(id=job_id, force=False)) == 0

    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "- 2026-09-30 · [분석] `다른작업` · a.pdf"
    assert len(lines) == 2 and f"[발표] `{job_id}`" in lines[1]
    assert (tmp_path / "최종" / "발표" / job_id / f"{job_id}_슬라이드.pdf").is_file()


def test_promote_holds_back_flagged_inspection(nlm, tmp_path):
    job_id = "발표_20261002"
    output = tmp_path / "작업" / job_id / "output"
    output.mkdir(parents=True)
    (output / "_nlm_run.json").write_text(json.dumps({
        "pack": "x.md", "inspection": {"slides.pdf": {"ok": True, "novel_numbers": ["83"]}},
    }), encoding="utf-8")
    assert nlm.cmd_promote(argparse.Namespace(id=job_id, force=False)) == 1
    assert not (tmp_path / "최종").exists()
