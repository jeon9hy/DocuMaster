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
    # 요르(Codex)의 중간 보고가 로그에서 피드로 올라온다
    yor_said = [e.get("text") for e in events if e["type"] == "agent.message" and e.get("agentId") == "yor"]
    assert any("핵심 질문 두 개" in (text or "") for text in yor_said)
    verdicts = [e["verdict"] for e in events if e["type"] == "validation.verdict"]
    assert verdicts == ["conditional"]
    assert events[-1]["type"] == "workflow.completed"
    # 완료 카드: 판정·REMOVE/CAUTION 수·걸린 시간·모델·최종 PDF를 이미 있는 값에서 모은다
    summary = events[-1]["summary"]
    assert (summary["verdict"], summary["removeCount"], summary["cautionCount"]) == ("conditional", 0, 1)
    assert summary["durationSeconds"] >= 0 and summary["models"]["loid"]
    assert summary["finalArtifactId"]
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
    # 로이드의 중간 보고와 완료 보고는 agent.message로 남는다(요르의 중간 보고는 따로)
    said = [e.get("agentId") for e in events_of(client, project_id) if e["type"] == "agent.message"]
    assert said.count("loid") == 2 and said.count("yor") == 1


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
        services.runs._record_turn(run_id, TurnResult(exit_code=0, model="claude-opus-5-5",
                                                     extra={"total_cost_usd": cumulative}))
    row = services.db.one("SELECT cost_usd, actual_model FROM runs WHERE id = ?", (run_id,))
    assert row["cost_usd"] == 3.0
    assert row["actual_model"] == "claude-opus-5-5"


def test_second_project_is_queued_and_starts_after_the_first_completes(client):
    first = create_project(client, "먼저")
    second = create_project(client, "나중")
    start(client, first, "첫 보고서를 써줘")
    prompt = pending_prompt(client, first)  # 첫 실행이 응답을 기다린다 = 아직 자리를 차지한다

    assert client.post(f"/api/projects/{second}/messages", json={"text": "둘째 보고서"}).status_code == 201
    busy = client.post(f"/api/projects/{second}/runs")
    assert busy.status_code == 409 and busy.json()["detail"]["code"] == "busy"
    queued = client.post(f"/api/projects/{second}/queue")
    assert queued.status_code == 202 and queued.json() == {"started": False, "position": 1}
    assert client.post(f"/api/projects/{second}/queue").status_code == 409  # 두 번 예약하지 않는다
    assert types_of(client, second)[-1] == "workflow.queued"

    answer(client, first, prompt["promptId"])
    wait_until(lambda: "workflow.completed" in types_of(client, first))
    wait_until(lambda: "workflow.started" in types_of(client, second))  # 앞 실행이 끝나자 예약이 시작됐다
    pending_prompt(client, second)
    assert client.delete(f"/api/projects/{second}/queue").status_code == 409  # 이미 시작해 예약이 없다


def test_queued_run_can_be_cancelled_and_empty_slot_starts_immediately(client):
    first = create_project(client, "먼저")
    second = create_project(client, "나중")
    start(client, first, "첫 보고서를 써줘")
    pending_prompt(client, first)
    client.post(f"/api/projects/{second}/messages", json={"text": "둘째 보고서"})
    assert client.post(f"/api/projects/{second}/queue").status_code == 202
    assert client.delete(f"/api/projects/{second}/queue").status_code == 204
    assert types_of(client, second)[-1] == "workflow.queue.cancelled"

    # 중지로 끝나면 예약은 기다린다(여기선 예약이 없으니 아무 일도 없다). 빈 자리에 예약하면 바로 시작한다
    assert client.post(f"/api/projects/{first}/runs/current/stop").status_code == 202
    wait_until(lambda: "workflow.stopped" in types_of(client, first))
    started = client.post(f"/api/projects/{second}/queue")
    assert started.status_code == 202 and started.json()["started"] is True


def test_permission_check_outage_resumes_once_then_completes(client, monkeypatch):
    """Claude Code auto 모드 안전 검사(서버 쪽)가 판정을 못 내 턴이 끝나면, 경고 뒤 같은 세션으로 한 번 이어 간다."""
    import app.runs as runs_module
    monkeypatch.setattr(runs_module, "PERMISSION_RETRY_SECONDS", 0)
    project_id = create_project(client, "안전 검사 장애")
    start(client, project_id, "보고서를 써줘 [noverdict]")
    prompt = pending_prompt(client, project_id)  # 이어 간 턴이 01을 마치고 기획 확인을 묻는다
    answer(client, project_id, prompt["promptId"])
    wait_until(lambda: "workflow.completed" in types_of(client, project_id))
    events = events_of(client, project_id)
    warnings = [e["message"] for e in events if e["type"] == "workflow.warning"]
    assert any("명령 안전 검사" in message and "일시 장애" in message for message in warnings)
    assert "workflow.failed" not in [e["type"] for e in events]


def test_permission_check_outage_twice_fails_with_a_clear_reason(client, monkeypatch):
    import app.runs as runs_module
    from app.orchestrator import ProcessTurn
    monkeypatch.setattr(runs_module, "PERMISSION_RETRY_SECONDS", 0)
    original_wait = ProcessTurn.wait

    def always_outage(self):
        result = original_wait(self)
        result.permission_check_failures = max(result.permission_check_failures, 1)
        result.exit_code = 1
        return result

    monkeypatch.setattr(ProcessTurn, "wait", always_outage)
    project_id = create_project(client, "계속 장애")
    start(client, project_id, "보고서를 써줘 [noverdict]")
    failed = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "workflow.failed"), None))
    assert "명령 안전 검사" in failed["reason"] and "에이전트 프로세스가 오류로" not in failed["reason"]


def finished_document(client) -> str:
    project_id = create_project(client, "첨삭 대상", "document")
    start(client, project_id, "주거 정책 보고서를 써줘 [autocontinue]")
    wait_until(lambda: "workflow.completed" in types_of(client, project_id))
    return project_id


def test_revise_writes_a_new_07_and_replaces_the_final_in_its_own_session(client, settings):
    project_id = finished_document(client)
    db = sqlite3.connect(settings.db_path)
    first_session = db.execute("SELECT session_id FROM projects WHERE id = ?", (project_id,)).fetchone()[0]

    response = client.post(f"/api/projects/{project_id}/revise", json={"text": "요약 문단이 딱딱해요. 부드럽게"})
    assert response.status_code == 202, response.text
    run_id = response.json()["runId"]
    wait_until(lambda: [e for e in events_of(client, project_id) if e["type"] == "workflow.completed"
                        and e.get("runId") == run_id])

    kind, session = db.execute("SELECT kind, session_id FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert kind == "revise" and session and session != first_session
    # 원래 작업 세션은 그대로다(첨삭이 긴 조사 세션을 이어 쓰지 않는다)
    assert db.execute("SELECT session_id FROM projects WHERE id = ?", (project_id,)).fetchone()[0] == first_session
    artifacts = {a["name"]: a for a in client.get(f"/api/projects/{project_id}/artifacts").json()}
    assert "07_final_document_v02.md" in artifacts
    # 이전판은 <ID>_v01.pdf로 남아 내부 작업물, 대표 최종본(<ID>.pdf)은 최신본
    previous = next(a for name, a in artifacts.items() if name.endswith("_v01.pdf"))
    assert previous["visibility"] == "internal"
    created = [e["artifact"] for e in events_of(client, project_id) if e["type"] == "artifact.created"]
    assert next(a for a in created if a["id"] == previous["id"])["summary"] == "이전 최종본 · v01"
    library = client.get("/api/library").json()
    assert [doc["fileName"] for doc in library if doc["projectId"] == project_id] == [
        previous["name"].replace("_v01.pdf", ".pdf")]
    user_said = [e["text"] for e in events_of(client, project_id) if e["type"] == "user.message"]
    assert user_said[-1].startswith(f"첨삭 요청 · {previous['name'].replace('_v01.pdf', '.pdf')}\n")


def test_revise_targets_one_of_several_final_pdfs(client, settings):
    project_id = finished_document(client)
    final = next((settings.repo_root / "webapp" / ".data" / "sandbox" / "최종").glob("*/*/*.pdf")).parent
    workspace_id = final.name
    practice = f"{workspace_id}_연습문제.pdf"
    (final / practice).write_bytes(b"%PDF-1.4 practice")
    main_before = (final / f"{workspace_id}.pdf").read_bytes()

    bad = client.post(f"/api/projects/{project_id}/revise", json={"text": "고쳐줘", "target": "없는파일.pdf"})
    assert bad.status_code == 400
    response = client.post(f"/api/projects/{project_id}/revise", json={"text": "풀이를 더 쉽게", "target": practice})
    assert response.status_code == 202, response.text
    run_id = response.json()["runId"]
    completed = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "workflow.completed"
                                         and e.get("runId") == run_id), None))

    # 고른 PDF만 새 버전이 되고 이전판을 남긴다 — 본문 PDF는 그대로
    assert (final / f"{workspace_id}_연습문제_v01.pdf").read_bytes() == b"%PDF-1.4 practice"
    assert (final / practice).read_bytes() != b"%PDF-1.4 practice"
    assert (final / f"{workspace_id}.pdf").read_bytes() == main_before
    assert not list(final.glob(f"{workspace_id}_v*.pdf"))
    artifacts = {a["name"]: a for a in client.get(f"/api/projects/{project_id}/artifacts").json()}
    assert artifacts[f"{workspace_id}_연습문제_v01.pdf"]["visibility"] == "internal"
    # 완료 카드는 최종 PDF를 모두 싣는다
    finals = completed["summary"]["finalArtifactIds"]
    assert sorted(artifacts[name]["id"] for name in (f"{workspace_id}.pdf", practice)) == sorted(finals)


def test_revise_only_for_finished_documents(client):
    project_id = create_project(client, "진행 중", "document")
    start(client, project_id, "보고서를 써줘")  # 기획 확인에서 멈춘다
    pending_prompt(client, project_id)
    response = client.post(f"/api/projects/{project_id}/revise", json={"text": "고쳐줘"})
    assert response.status_code in (400, 409)
    assert client.post(f"/api/projects/{project_id}/revise", json={"text": " "}).status_code == 400


def test_stopped_revise_restores_finished_state(client, settings):
    project_id = finished_document(client)
    response = client.post(f"/api/projects/{project_id}/revise", json={"text": "새 통계를 넣어줘 [revise-none]"})
    assert response.status_code == 202, response.text
    request = pending_prompt(client, project_id)
    assert request["title"].startswith("사용자 승인 대기")
    assert client.post(f"/api/projects/{project_id}/runs/current/stop").status_code == 202
    wait_until(lambda: "workflow.stopped" in types_of(client, project_id))
    state = next((settings.repo_root / "webapp" / ".data" / "sandbox" / "작업").glob("*/상태.md"))
    assert "상태: 완료" in state.read_text(encoding="utf-8")


def test_revise_cut_by_usage_limit_resumes_in_the_same_session(client, settings):
    project_id = finished_document(client)
    final = next((settings.repo_root / "webapp" / ".data" / "sandbox" / "최종").glob("*/*/*.pdf")).parent
    workspace_id = final.name
    practice = f"{workspace_id}_연습문제.pdf"
    (final / practice).write_bytes(b"%PDF-1.4 practice")
    response = client.post(f"/api/projects/{project_id}/revise",
                           json={"text": "수식을 한 줄로 [revise-limit]", "target": practice})
    first_run = response.json()["runId"]
    failed = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "workflow.failed"), None))
    # 한도 이유와 풀리는 시각을 알리고, 원래 작업의 단계는 건드리지 않는다
    assert "사용량 한도" in failed["reason"] and "3:10pm (Asia/Seoul)" in failed["reason"] and failed["revise"] is True
    paused = wait_until(lambda: next((e for e in events_of(client, project_id) if e["type"] == "revise.paused"), None))
    assert paused["target"] == practice
    state = next((settings.repo_root / "webapp" / ".data" / "sandbox" / "작업").glob("*/상태.md"))
    assert "상태: 완료" in state.read_text(encoding="utf-8")

    # 완료된 작업이어도 실행 버튼이 같은 세션으로 첨삭을 잇는다. 기다리는 동안 보낸 지시도 함께 넘긴다
    assert client.post(f"/api/projects/{project_id}/messages", json={"text": "하던 작업 이어서"}).status_code == 201
    response = client.post(f"/api/projects/{project_id}/runs")
    assert response.status_code == 202, response.text
    second_run = response.json()["runId"]
    wait_until(lambda: [e for e in events_of(client, project_id)
                        if e["type"] == "workflow.completed" and e.get("runId") == second_run])
    db = sqlite3.connect(settings.db_path)
    rows = dict(db.execute("SELECT id, session_id FROM runs WHERE id IN (?, ?)", (first_run, second_run)).fetchall())
    assert rows[first_run] == rows[second_run]
    assert db.execute("SELECT kind, revise_target FROM runs WHERE id = ?", (second_run,)).fetchone() == (
        "revise", practice)
    # 고르던 PDF만 새 버전이 된다
    assert (final / f"{workspace_id}_연습문제_v01.pdf").read_bytes() == b"%PDF-1.4 practice"
    assert not list(final.glob(f"{workspace_id}_v*.pdf"))
    # 끝난 뒤에는 다시 「이미 완료」
    assert client.post(f"/api/projects/{project_id}/runs").status_code == 400


def test_restart_backfills_paused_revise_from_older_runs(settings):
    with owner_client(settings) as client:
        project_id = finished_document(client)
        client.post(f"/api/projects/{project_id}/revise", json={"text": "고쳐줘 [revise-limit]"})
        wait_until(lambda: "revise.paused" in types_of(client, project_id))
    db = sqlite3.connect(settings.db_path)
    # 이 기능 전의 기록처럼: 대상 열과 알림이 없다
    db.execute("UPDATE runs SET revise_target = NULL WHERE kind = 'revise'")
    db.execute("DELETE FROM events WHERE type = 'revise.paused'")
    db.commit()
    with owner_client(settings) as client:
        paused = next(e for e in events_of(client, project_id) if e["type"] == "revise.paused")
        assert paused["target"].endswith(".pdf")
