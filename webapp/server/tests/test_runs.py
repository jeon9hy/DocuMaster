"""가짜 오케스트레이터로 실행 전체 경로를 검증한다(프로세스 실행 → 파일 감시 → 이벤트 → 응답 → 재개)."""

import sqlite3
from dataclasses import replace

from app.orchestrator import TurnResult


from .conftest import owner_client, create_project, events_of, types_of, wait_until


def start(client, project_id: str, text: str) -> None:
    assert client.post(f"/api/projects/{project_id}/messages", json={"text": text}).status_code == 201
    response = client.post(f"/api/projects/{project_id}/runs")
    assert response.status_code == 202, response.text


def pending_prompt(client, project_id: str) -> dict:
    return wait_until(lambda: next((e["request"] for e in reversed(events_of(client, project_id))
                                    if e["type"] == "user.input.required"), None))


def answer(client, project_id: str, prompt_id: str, text: str = "네, 진행하세요") -> None:
    response = client.post(f"/api/projects/{project_id}/inputs/{prompt_id}/response", json={"answer": text})
    assert response.status_code == 202, response.text


def test_full_run_with_user_input_then_completion(client, settings):
    project_id = create_project(client, "주거 보고서")
    start(client, project_id, "2026 주거 정책 보고서를 써줘")

    request = pending_prompt(client, project_id)
    assert request["title"].startswith("사용자 승인 대기")
    assert "자료조사를 시작할까요" in request["message"]
    types = types_of(client, project_id)
    assert "project.mode.decided" in types  # 자동 판정 → 00의 모드: DOCUMENT
    assert client.get("/api/projects").json()[0]["mode"] == "document"

    answer(client, project_id, request["promptId"])
    wait_until(lambda: "workflow.completed" in types_of(client, project_id))

    events = events_of(client, project_id)
    completed = [e["stageId"] for e in events if e["type"] == "workflow.stage.completed"]
    assert completed == ["requirements", "planning", "research", "validation", "writing", "finalReview"]
    started = [e["stageId"] for e in events if e["type"] == "workflow.stage.started"]
    assert started == ["requirements", "planning", "research", "validation", "writing", "finalReview"]
    # 파일 계약 순서대로 일한 에이전트(문서 모드: 05 뒤 아냐가 07)
    agents = [e["agentId"] for e in events if e["type"] == "agent.started"]
    assert agents == ["loid", "loid", "yor", "yuri", "yor", "yuri", "anya", "loid"]
    verdicts = [e["verdict"] for e in events if e["type"] == "validation.verdict"]
    assert verdicts == ["conditional"]
    assert events[-1]["type"] == "workflow.completed"
    assert events[-2] == {**events[-2], "type": "agent.message", "agentId": "loid"}
    assert all(e["runId"] for e in events if e["type"] != "user.message")

    artifacts = client.get(f"/api/projects/{project_id}/artifacts").json()
    names = {a["name"]: a for a in artifacts}
    assert names["05_verified_research_pack.md"]["visibility"] == "primary"
    assert names["03_verification_questions.md"]["visibility"] == "internal"
    final = next(a for a in artifacts if a["relativePath"].startswith("webapp/.data/sandbox/최종/"))
    content = client.get(f"/api/projects/{project_id}/artifacts/{final['id']}/content").json()
    assert content["type"] == "pdf" and content["src"].endswith("/download?inline=1")
    download = client.get(f"/api/projects/{project_id}/artifacts/{final['id']}/download")
    assert download.status_code == 200 and download.content.startswith(b"%PDF")
    markdown = client.get(f"/api/projects/{project_id}/artifacts/{names['00_user_brief.md']['id']}/content").json()
    assert markdown["type"] == "markdown" and "모드: DOCUMENT" in markdown["text"]


def test_prompt_is_the_users_request_plus_references_only(client, settings):
    project_id = create_project(client, "발표", "presentation")
    client.post(f"/api/projects/{project_id}/references", data={"source": "url", "url": "https://example.org/a"})
    start(client, project_id, "치이카와 세계관 발표자료 만들어줘")
    pending_prompt(client, project_id)
    workspace = next((settings.sandbox_root / "작업").iterdir())
    sent = (workspace / "_요청.txt").read_text(encoding="utf-8")
    assert sent == "치이카와 세계관 발표자료 만들어줘\n\n형식: 발표(PRESENTATION)\n\n참고자료:\n- https://example.org/a"


def test_run_requires_a_request_and_blocks_duplicates(settings):
    with owner_client(replace(settings, fake_step_seconds=0.3)) as client:
        project_id = create_project(client)
        empty = client.post(f"/api/projects/{project_id}/runs")
        assert empty.status_code == 400 and "요청" in empty.json()["detail"]["message"]
        start(client, project_id, "보고서")
        assert client.post(f"/api/projects/{project_id}/runs").status_code == 409
        other = create_project(client, "다른 프로젝트")
        client.post(f"/api/projects/{other}/messages", json={"text": "다른 요청"})
        conflict = client.post(f"/api/projects/{other}/runs")
        assert conflict.status_code == 409 and "한 번에 하나" in conflict.json()["detail"]["message"]
        client.post(f"/api/projects/{project_id}/runs/current/stop")
        wait_until(lambda: "workflow.stopped" in types_of(client, project_id))


def test_graceful_stop_waits_for_the_current_stage_then_resumes(settings):
    with owner_client(replace(settings, fake_step_seconds=0.5)) as client:
        project_id = create_project(client)
        start(client, project_id, "보고서를 써줘")
        wait_until(lambda: "agent.started" in types_of(client, project_id))
        assert client.post(f"/api/projects/{project_id}/runs/current/stop").status_code == 202
        wait_until(lambda: "workflow.stopped" in types_of(client, project_id))
        types = types_of(client, project_id)
        # 중지 요청 뒤 진행 중이던 단계(요구분석)가 끝난 다음에 멈춘다
        assert types.index("workflow.stop.requested") < types.index("workflow.stage.completed") \
            < types.index("workflow.stopped")
        assert "user.input.required" not in types

        # 다시 실행하면 같은 세션을 이어서(--resume) 멈춘 곳부터
        assert client.post(f"/api/projects/{project_id}/runs").status_code == 202
        request = pending_prompt(client, project_id)
        assert "01 기획을 마쳤습니다" in request["message"]


def test_stop_while_awaiting_input_is_immediate(client):
    project_id = create_project(client)
    start(client, project_id, "보고서")
    pending_prompt(client, project_id)
    assert client.post(f"/api/projects/{project_id}/runs/current/stop").status_code == 202
    assert types_of(client, project_id)[-1] == "workflow.stopped"


def test_blocked_verdict_asks_user_and_continues_after_answer(client):
    project_id = create_project(client)
    start(client, project_id, "보고서 [blocked]")
    answer(client, project_id, pending_prompt(client, project_id)["promptId"])
    wait_until(lambda: any(e["type"] == "validation.verdict" for e in events_of(client, project_id)))
    blocked = wait_until(lambda: [e for e in events_of(client, project_id) if e["type"] == "user.input.required"][1:])
    assert "검증 보류" in blocked[0]["request"]["title"]
    answer(client, project_id, blocked[0]["request"]["promptId"], "주장 A를 제거하고 계속")
    wait_until(lambda: "workflow.completed" in types_of(client, project_id))
    verdicts = [e["verdict"] for e in events_of(client, project_id) if e["type"] == "validation.verdict"]
    assert verdicts == ["blocked", "conditional"]


def test_agent_process_error_is_reported_with_reason(client):
    project_id = create_project(client)
    start(client, project_id, "보고서 [fail]")
    failed = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "workflow.failed"), None))
    assert "에이전트 프로세스가 오류로 끝났습니다" in failed["reason"]
    assert "[fail]" in failed["reason"]


def test_restart_recovers_interrupted_runs_and_keeps_pending_input(settings):
    with owner_client(settings) as client:
        project_id = create_project(client)
        start(client, project_id, "보고서")
        prompt_id = pending_prompt(client, project_id)["promptId"]

    # 꺼질 때 돌고 있던 실행(프로세스 없음)을 흉내 낸다
    other_id = "p_interrupted"
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("INSERT INTO projects (id, display_name, description, mode, workspace_id, work_root, source,"
                     " session_id, created_at, updated_at) VALUES (?, '끊긴 실행', '', 'auto', NULL,"
                     " 'webapp/.data/sandbox', 'web', NULL, '2026-09-19', '2026-09-19')", (other_id,))
        conn.execute("INSERT INTO runs (id, project_id, status, current_stage, started_at)"
                     " VALUES ('run_x', ?, 'running', 'research', '2026-09-19')", (other_id,))

    with owner_client(settings) as client:
        assert types_of(client, other_id)[-2:] == ["workflow.warning", "workflow.stopped"]
        # 응답 대기 실행은 재시작 뒤에도 답할 수 있다(같은 세션으로 이어짐)
        answer(client, project_id, prompt_id)
        wait_until(lambda: "workflow.completed" in types_of(client, project_id))


# --- 멈춤 규칙: 구조화된 상태로만 판단한다 ---------------------------------------------


def test_normal_turn_end_continues_automatically_without_asking(client):
    project_id = create_project(client)
    start(client, project_id, "보고서 [autocontinue]")
    wait_until(lambda: "workflow.completed" in types_of(client, project_id))
    types = types_of(client, project_id)
    assert "user.input.required" not in types
    # 로이드의 중간 보고와 완료 보고는 agent.message로 남는다
    assert types.count("agent.message") == 2


def test_turn_ending_before_workspace_exists_asks_user(client):
    project_id = create_project(client)
    start(client, project_id, "뭔가 만들어줘 [ambiguous]")
    request = pending_prompt(client, project_id)
    assert request["title"] == "로이드의 확인 요청 · 작업 시작 전"
    assert "어느 형식" in request["message"]
    answer(client, project_id, request["promptId"], "발표로 해줘")
    second = wait_until(lambda: [e for e in events_of(client, project_id) if e["type"] == "user.input.required"][1:])
    assert second[0]["request"]["title"].startswith("사용자 승인 대기")
    assert client.get("/api/projects").json()[0]["mode"] == "presentation"


def test_preworkspace_prompt_does_not_repeat_forever(client):
    project_id = create_project(client)
    start(client, project_id, "뭔가 만들어줘 [ambiguous]")
    first = pending_prompt(client, project_id)
    answer(client, project_id, first["promptId"], "아직도 묻기 [ambiguous]")
    failed = wait_until(lambda: next(
        (event for event in events_of(client, project_id) if event["type"] == "workflow.failed"), None
    ))
    assert "작업 폴더를 만들지 않아" in failed["reason"]
    assert types_of(client, project_id).count("user.input.required") == 1


def test_repeated_turns_without_progress_fail_instead_of_looping(client):
    project_id = create_project(client)
    start(client, project_id, "보고서 [autocontinue] [stall]")
    failed = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "workflow.failed"), None))
    assert "진행하지 않은 채" in failed["reason"]
    assert "user.input.required" not in types_of(client, project_id)


def test_cumulative_claude_cost_is_not_added_twice(client, settings):
    project_id = create_project(client)
    services = client.app.state.services
    run_id = "run_cost"
    services.db.execute("INSERT INTO runs (id, project_id, status, started_at) VALUES (?, ?, 'completed', '2026-09-20')",
                        (run_id, project_id))
    for cumulative in (1.1, 1.1, 2.5, 3.0):
        services.runs._record_turn(run_id, TurnResult(exit_code=0, model="claude-opus-5",
                                                     extra={"total_cost_usd": cumulative}))
    row = services.db.one("SELECT cost_usd, actual_model FROM runs WHERE id = ?", (run_id,))
    assert row["cost_usd"] == 3.0
    assert row["actual_model"] == "claude-opus-5"
