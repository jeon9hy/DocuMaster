"""요르 호출 도구(.claude/tools/yor.py) — 가짜 codex로 명령 조립·입력 인라인·세션·패치 적용·모델 대조를 확인한다."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).parents[3] / ".claude" / "tools" / "yor.py"
ID = "테스트_20260927"

FAKE_CODEX = r'''
import json, os, sys
args = sys.argv[1:]
prompt = sys.stdin.buffer.read().decode("utf-8")
out = args[args.index("-o") + 1]
model = os.environ.get("FAKE_ACTUAL_MODEL") or args[args.index("-m") + 1]
effort = next(a.split("=", 1)[1] for a in args if a.startswith("model_reasoning_effort="))
session = args[args.index("resume") + 1] if "resume" in args else "sess-" + str(len(prompt))
sandbox = "read-only" if "read-only" in args or 'sandbox_mode="read-only"' in args else "workspace-write"
# --json: 기계용 이벤트는 stdout, 모델·강도·샌드박스는 세션 기록(rollout)에만 있다(실제 codex 0.154와 같은 모양)
assert "--json" in args
if not os.environ.get("FAKE_NO_THREAD_EVENT"):
    print(json.dumps({"type": "thread.started", "thread_id": session}))
print(json.dumps({"type": "turn.started"}))
print(json.dumps({"type": "item.completed", "item": {"id": "i1", "type": "agent_message", "text": "진행 보고"}}))
day = os.path.join(os.environ["CODEX_HOME"], "sessions", "2026", "09", "28")
os.makedirs(day, exist_ok=True)
with open(os.path.join(day, "rollout-2026-09-28T10-00-00-%s.jsonl" % session), "a", encoding="utf-8") as rollout:
    rollout.write(json.dumps({"type": "session_meta", "payload": {"id": session, "cwd": os.getcwd(),
                                                                  "originator": "codex_exec"}}) + "\n")
    rollout.write(json.dumps({"type": "turn_context", "payload": {"model": model, "effort": effort,
                                                                  "sandbox_policy": {"type": sandbox}}}) + "\n")
with open(os.environ["FAKE_ARGS_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "prompt": prompt}, ensure_ascii=False) + "\n")
with open(out, "w", encoding="utf-8") as handle:
    handle.write(os.environ.get("FAKE_OUTPUT", "# Research Pack\n- 작업 ID\n--- 헤더 끝 ---\n본문\n"))
code = int(os.environ.get("FAKE_EXIT", "0"))
if code:
    print(json.dumps({"type": "turn.failed", "error": {"message": "가짜 실패"}}))
else:
    print(json.dumps({"type": "turn.completed", "usage": {}}))
sys.exit(code)
'''


@pytest.fixture
def env(tmp_path):
    fake = tmp_path / "fake_codex.py"
    fake.write_text(FAKE_CODEX, encoding="utf-8")
    ws = tmp_path / "작업" / ID / "workspace"
    ws.mkdir(parents=True)
    (ws / "00_user_brief.md").write_text("# User Brief\n- 모드: PRESENTATION\n- 덱 유형: 학술 (연구)\n", encoding="utf-8")
    (ws / "01_research_blueprint.md").write_text("# Research Blueprint\n질문 Q1\n", encoding="utf-8")
    models = tmp_path / "models.json"
    models.write_text(json.dumps({"yor": {"model": "gpt-test", "effort": "medium"}}), encoding="utf-8")
    values = {**os.environ, "DOCUMASTER_WORK_ROOT": str(tmp_path), "DOCUMASTER_CODEX": json.dumps([sys.executable, str(fake)]),
              "DOCUMASTER_AGENT_MODELS": str(models), "FAKE_ARGS_LOG": str(tmp_path / "calls.jsonl"),
              "CODEX_HOME": str(tmp_path / "codex_home"),
              "PYTHONIOENCODING": "utf-8"}
    return tmp_path, ws, values


def run(values: dict, *args: str, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args, "--id", ID], capture_output=True, text=True,
                          encoding="utf-8", env={**values, **extra}, check=False)


def calls(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / "calls.jsonl").read_text(encoding="utf-8").splitlines()]


def test_research_inlines_inputs_uses_snapshot_and_records_session(env):
    root, ws, values = env
    result = run(values, "research")
    assert result.returncode == 0, result.stdout
    assert "요르 research: OK" in result.stdout and "실제 gpt-test/medium" in result.stdout
    call = calls(root)[0]
    assert call["args"][call["args"].index("-m") + 1] == "gpt-test"
    assert "model_reasoning_effort=medium" in call["args"] and "tools.web_search=true" in call["args"]
    assert "read-only" in call["args"] and "resume" not in call["args"]
    # 입력 파일은 경로가 아니라 전문으로 붙는다(E-051)
    assert "질문 Q1" in call["prompt"] and "===== 입력 파일: workspace/00_user_brief.md" in call["prompt"]
    assert "# 요르 — " in call["prompt"]  # 역할 파일이 붙었다
    sessions = json.loads((root / "작업" / ID / "_yor_sessions.json").read_text(encoding="utf-8"))
    assert sessions["research"].startswith("sess-")
    assert (ws / "02_research_pack.md").read_text(encoding="utf-8").startswith("# Research Pack")
    state = json.loads((root / "작업" / ID / "_yor_call.json").read_text(encoding="utf-8"))
    assert state["status"] == "done" and state["exit"] == 0


def test_answer_resumes_research_session_and_applies_patch(env):
    root, ws, values = env
    run(values, "research")
    (ws / "02_research_pack.md").write_text("# Research Pack\n--- 헤더 끝 ---\n| S01 | 값 10 |\n", encoding="utf-8")
    (ws / "03_verification_questions.md").write_text("# 검증 질문\n### V-001\n", encoding="utf-8")
    raw = ("=== 응답 시작 ===\n## V-001\n응답: 수정\n=== 응답 끝 ===\n"
           "=== 수정 패치 시작 ===\n--- PATCH 1 ---\n대상: §C\nOLD:\n| S01 | 값 10 |\nNEW:\n| S01 | 값 12 |\n"
           "--- PATCH 끝 ---\n=== 수정 패치 끝 ===\n")
    result = run(values, "answer", FAKE_OUTPUT=raw)
    assert result.returncode == 0, result.stdout
    session = json.loads((root / "작업" / ID / "_yor_sessions.json").read_text(encoding="utf-8"))["research"]
    call = calls(root)[-1]
    assert call["args"][call["args"].index("resume") + 1] == session and "-C" not in call["args"]
    assert 'sandbox_mode="read-only"' in call["args"]  # resume은 샌드박스를 잇지 않는다 — 명시한다
    assert "### V-001" in call["prompt"] and "샌드박스" not in result.stdout
    assert "값 12" in (ws / "02_research_pack_v02.md").read_text(encoding="utf-8")
    assert (ws / "04_verification_answers.md").read_text(encoding="utf-8").startswith("## V-001")


def test_failed_patch_writes_nothing_and_points_to_nearest_line(env):
    root, ws, values = env
    run(values, "research")
    (ws / "02_research_pack.md").write_text("| **S01** | 값 10 |\n", encoding="utf-8")
    (ws / "03_verification_questions.md").write_text("질문\n", encoding="utf-8")
    raw = ("=== 응답 시작 ===\nok\n=== 응답 끝 ===\n=== 수정 패치 시작 ===\n--- PATCH 1 ---\nOLD:\n| S01 | 값 10 |\n"
           "NEW:\n| S01 | 값 12 |\n--- PATCH 끝 ---\n=== 수정 패치 끝 ===\n")
    result = run(values, "answer", FAKE_OUTPUT=raw)
    assert result.returncode == 1
    assert "가장 가까운 줄" in result.stdout and "**S01**" in result.stdout
    assert not (ws / "02_research_pack_v02.md").exists()

    # --retry는 패치만 다시 받는다 — 응답 블록이 없어도 첫 응답의 04를 두고 패치를 적용한다
    (root / "작업" / ID / "_입력_응답.md").write_text("OLD를 `| **S01** | 값 10 |`로", encoding="utf-8")
    retry = ("=== 수정 패치 시작 ===\n--- PATCH 1 ---\nOLD:\n| **S01** | 값 10 |\n"
             "NEW:\n| **S01** | 값 12 |\n--- PATCH 끝 ---\n=== 수정 패치 끝 ===\n")
    result = run(values, "answer", "--retry", FAKE_OUTPUT=retry)
    assert result.returncode == 0, result.stdout
    assert "값 12" in (ws / "02_research_pack_v02.md").read_text(encoding="utf-8")
    assert (ws / "04_verification_answers.md").read_text(encoding="utf-8") == "ok\n"


def test_model_mismatch_in_log_fails(env):
    _, _, values = env
    result = run(values, "research", FAKE_ACTUAL_MODEL="gpt-other")
    assert result.returncode == 3 and "설정과 다르다" in result.stdout


def test_unreadable_snapshot_refuses_to_call(env):
    root, _, values = env
    result = run({**values, "DOCUMASTER_AGENT_MODELS": str(root / "missing.json")}, "research")
    assert result.returncode == 2 and "기본값으로 대신하지 않는다" in result.stdout
    assert not (root / "calls.jsonl").exists()


def test_plan_requires_decision_note_and_loads_one_deck_type(env):
    root, ws, values = env
    (ws / "05_verified_research_pack.md").write_text("검증 통과 — 이상 없음\n# Verified\n", encoding="utf-8")
    result = run(values, "plan")
    assert result.returncode == 2 and "_입력_세부기획.md" in result.stdout
    (root / "작업" / ID / "_입력_세부기획.md").write_text("채택: 없음\n", encoding="utf-8")
    result = run(values, "plan", FAKE_OUTPUT="# Detailed Plan\n--- 헤더 끝 ---\n")
    assert result.returncode == 0, result.stdout
    prompt = calls(root)[-1]["prompt"]
    assert "덱 유형 — 학술" in prompt and "덱 유형 — 스토리" not in prompt
    assert "web_search" not in " ".join(calls(root)[-1]["args"])


def test_resume_without_recorded_session_is_refused(env):
    _, _, values = env
    result = run(values, "pack")
    assert result.returncode == 2 and "세션 ID" in result.stdout


def test_wait_reports_finished_call(env):
    _, _, values = env
    run(values, "research")
    result = run(values, "wait")
    assert result.returncode == 0 and "요르 research: OK" in result.stdout


def test_json_events_go_to_their_own_log_and_session_falls_back_to_rollout(env):
    root, _, values = env
    result = run(values, "research", FAKE_NO_THREAD_EVENT="1")  # thread.started가 없어도 세션 기록에서 찾는다
    assert result.returncode == 0, result.stdout
    assert "실제 gpt-test/medium" in result.stdout
    base = root / "작업" / ID
    assert json.loads((base / "_yor_sessions.json").read_text(encoding="utf-8"))["research"].startswith("sess-")
    events = [json.loads(line) for line in (base / "_log_02.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["type"] == "turn.completed"
    assert json.loads((base / "_yor_call.json").read_text(encoding="utf-8"))["status"] == "done"


def test_failed_turn_reports_the_event_message(env):
    _, _, values = env
    result = run(values, "research", FAKE_EXIT="1")
    assert result.returncode == 1 and "가짜 실패" in result.stdout
