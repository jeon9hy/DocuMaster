
from .conftest import owner_client, create_project, events_of, wait_until


def test_project_crud_and_persistence_across_restart(settings):
    with owner_client(settings) as client:
        project_id = create_project(client, "주거 보고서", "document")
        client.post(f"/api/projects/{project_id}/messages", json={"text": "보고서를 써줘"})
        assert [p["name"] for p in client.get("/api/projects").json()] == ["주거 보고서"]

    # 백엔드 재시작 → 프로젝트와 이벤트가 그대로 있다
    with owner_client(settings) as client:
        projects = client.get("/api/projects").json()
        assert len(projects) == 1
        assert {key: projects[0][key] for key in ("id", "name", "description", "mode", "readOnly")} == {
            "id": project_id, "name": "주거 보고서", "description": "", "mode": "document", "readOnly": False}
        assert projects[0]["lastActivityAt"]
        snapshot = client.get(f"/api/projects/{project_id}/workspace").json()
        assert snapshot["lastEventSeq"] == 1
        assert snapshot["events"][0]["type"] == "user.message"


def test_event_envelope_and_sequence(client):
    project_id = create_project(client)
    for text in ("하나", "둘", "셋"):
        client.post(f"/api/projects/{project_id}/messages", json={"text": text})
    events = events_of(client, project_id)
    assert [event["seq"] for event in events] == [1, 2, 3]
    assert set(events[0]) >= {"schemaVersion", "id", "projectId", "runId", "seq", "at", "type", "text"}
    assert events[0]["schemaVersion"] == 1 and events[0]["runId"] is None


def test_validation_errors_are_explained(client):
    assert client.post("/api/projects", json={"name": " ", "mode": "auto"}).status_code == 400
    assert client.post("/api/projects", json={"name": "x", "mode": "weird"}).status_code == 400
    missing = client.get("/api/projects/nope/workspace")
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "not_found"


def test_health_reports_tool_presence_without_calling_models(client):
    health = client.get("/api/system/health").json()
    assert health["orchestrator"] == "fake"
    assert set(health["tools"]) == {"claude", "codex", "nlm"}
    assert all(isinstance(value, bool) for value in health["tools"].values())


def test_delete_hides_project_but_keeps_files_and_is_not_reimported(settings):
    work = settings.repo_root / "작업" / "옛작업_20260101"
    work.mkdir(parents=True)
    (work / "상태.md").write_text("# 옛작업_20260101 — 옛 작업 · 모드: DOCUMENT\n상태: 완료\n", encoding="utf-8")
    with owner_client(settings) as client:
        imported = client.get("/api/projects").json()[0]["id"]
        web = create_project(client, "지울 것")
        client.post(f"/api/projects/{web}/messages", json={"text": "보고서"})
        assert client.post(f"/api/projects/{web}/runs").status_code == 202
        busy = client.delete(f"/api/projects/{web}")
        assert busy.status_code == 409  # 실행 중에는 못 지운다
        client.post(f"/api/projects/{web}/runs/current/stop")
        wait_until(lambda: client.delete(f"/api/projects/{web}").status_code == 204)
        assert client.delete(f"/api/projects/{imported}").status_code == 204
        assert client.get("/api/projects").json() == []
        assert client.get(f"/api/projects/{web}/workspace").status_code == 404
    assert (work / "상태.md").exists()  # 파일은 그대로
    with owner_client(settings) as client:  # 재시작해도 가져오기가 되살리지 않는다
        assert client.get("/api/projects").json() == []
