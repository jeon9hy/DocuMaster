"""모델 설정: Owner만 · 지원 값만 · 실행 시작 때 스냅샷 · 조용한 대체 없음."""

from dataclasses import replace
import json
from pathlib import Path
import sqlite3

import pytest

from app.agent_settings import UnsupportedConfigError, check_model_calls, codex_models, orchestrator_models
from app.orchestrator import ClaudeCodeOrchestratorAdapter, TurnRequest

from .conftest import create_project, wait_until
from .test_runs import pending_prompt, start

OPUS_HIGH = {"provider": "anthropic", "modelId": "claude-opus-5-5", "reasoningLevel": "high"}


def by_agent(rows: list[dict]) -> dict[str, dict]:
    return {row["agentId"]: row for row in rows}


def test_defaults_match_claude_md_placement(client):
    rows = by_agent(client.get("/api/settings/agents").json())
    assert rows["yor"]["config"] == {"provider": "openai", "modelId": "gpt-5.6-sol", "reasoningLevel": "xhigh"}
    assert rows["yuri"]["config"]["modelId"] == "claude-sonnet-5-5"
    assert rows["anya"]["config"]["modelId"] == "claude-opus-5-5"
    assert rows["loid"]["config"] == OPUS_HIGH
    assert "claude-code-default" not in rows["loid"]["modelIds"] and None not in rows["loid"]["reasoningLevels"]
    assert all(not row["overridden"] for row in rows.values())
    # 모델 선택이 없는 본드만 잠긴다. 유리·아냐는 추론 강도를 넘길 방법이 없어 「도구 기본값」 하나뿐
    assert rows["bond"]["lockedReason"]
    assert all(rows[agent]["lockedReason"] is None for agent in ("loid", "yor", "yuri", "anya"))
    assert rows["yuri"]["reasoningLevels"] == [None] and rows["yuri"]["config"]["reasoningLevel"] is None
    assert "claude-haiku-4-5" in rows["anya"]["modelIds"]


def test_owner_can_change_loid_and_reset(client):
    sonnet_max = {"provider": "anthropic", "modelId": "claude-sonnet-5-5", "reasoningLevel": "max"}
    rows = by_agent(client.patch("/api/settings/agents/loid", json=sonnet_max).json())
    assert rows["loid"]["config"] == sonnet_max and rows["loid"]["overridden"] and rows["loid"]["updatedAt"]
    rows = by_agent(client.delete("/api/settings/agents/loid").json())
    assert rows["loid"]["config"] == OPUS_HIGH and not rows["loid"]["overridden"]
    assert rows["loid"]["updatedAt"]  # 되돌린 것도 마지막 변경으로 남는다


def test_saved_claude_code_default_fills_only_the_empty_parts(client):
    service = client.app.state.services.agent_settings
    service._save("loid", {"provider": "anthropic", "modelId": "claude-code-default", "reasoningLevel": None})
    assert by_agent(client.get("/api/settings/agents").json())["loid"]["config"] == OPUS_HIGH
    service._save("loid", {"provider": "anthropic", "modelId": "claude-haiku-4-5", "reasoningLevel": None})
    assert by_agent(client.get("/api/settings/agents").json())["loid"]["config"]["modelId"] == "claude-haiku-4-5"


def test_saved_old_model_id_moves_to_its_successor(client):
    client.app.state.services.agent_settings._save("anya", {"provider": "anthropic", "modelId": "claude-opus-5", "reasoningLevel": None})
    assert by_agent(client.get("/api/settings/agents").json())["anya"]["config"]["modelId"] == "claude-opus-5-5"
    client.app.state.services.agent_settings._save("yuri", {"provider": "anthropic", "modelId": "claude-sonnet-5", "reasoningLevel": None})
    assert by_agent(client.get("/api/settings/agents").json())["yuri"]["config"]["modelId"] == "claude-sonnet-5-5"


def test_unsupported_settings_are_refused_not_substituted(client):
    cases = [
        ("yor", {"provider": "openai", "modelId": "gpt-imaginary", "reasoningLevel": "xhigh"}),
        ("yuri", {"provider": "anthropic", "modelId": "claude-opus-5-5", "reasoningLevel": "high"}),
        ("bond", {"provider": "google", "modelId": "gemini", "reasoningLevel": None}),
        ("loid", {"provider": "anthropic", "modelId": "claude-imaginary", "reasoningLevel": "high"}),
        ("loid", {"provider": "openai", "modelId": "claude-opus-5-5", "reasoningLevel": "high"}),
        ("loid", {"provider": "anthropic", "modelId": "claude-code-default", "reasoningLevel": "high"}),
        ("loid", {"provider": "anthropic", "modelId": "claude-opus-5-5", "reasoningLevel": None}),
    ]
    for agent_id, config in cases:
        response = client.patch(f"/api/settings/agents/{agent_id}", json=config)
        assert response.status_code == 400, (agent_id, config)
        message = response.json()["detail"]["message"]
        assert ("Codex 모델 목록" in message if agent_id == "yor"
                else message == "현재 선택한 모델 설정을 사용할 수 없습니다.")
    assert all(not row["overridden"] for row in client.get("/api/settings/agents").json())
    assert client.patch("/api/settings/agents/nobody", json=OPUS_HIGH).status_code == 404


def test_run_keeps_the_config_it_started_with(client, settings):
    client.patch("/api/settings/agents/loid", json=OPUS_HIGH)
    project_id = create_project(client)
    start(client, project_id, "보고서")
    pending_prompt(client, project_id)
    # 실행 중(응답 대기)에 설정을 바꿔도 이 실행의 스냅샷은 그대로다
    client.patch("/api/settings/agents/loid", json={**OPUS_HIGH, "reasoningLevel": "max"})
    with sqlite3.connect(settings.db_path) as conn:
        snapshot = json.loads(conn.execute("SELECT agent_config_json FROM runs").fetchone()[0])
    assert snapshot["loid"] == OPUS_HIGH
    assert snapshot["yor"]["modelId"] == "gpt-5.6-sol"


def test_claude_adapter_passes_loid_model_only_when_set(settings):
    adapter = ClaudeCodeOrchestratorAdapter(settings)

    def command(configs: dict) -> list[str]:
        return adapter.build_command(TurnRequest(prompt="x", session_id="s", resume=False, work_root=Path("."),
                                                 log_path=Path("x.jsonl"), agent_configs=configs))

    default = command({"loid": {"provider": "anthropic", "modelId": "claude-code-default", "reasoningLevel": None}})
    assert "--model" not in default and "--effort" not in default
    chosen = command({"loid": OPUS_HIGH})
    assert chosen[chosen.index("--model") + 1] == "claude-opus-5-5"
    assert chosen[chosen.index("--effort") + 1] == "high"
    assert "--fallback-model" not in chosen


def write_codex_cache(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "models_cache.json").write_text(json.dumps({"models": [
        {"slug": "gpt-5.6-sol", "visibility": "list", "supported_reasoning_levels": [
            {"effort": "low"}, {"effort": "xhigh"}, {"effort": "ultra"}]},
        {"slug": "gpt-5.5", "visibility": "list", "supported_reasoning_levels": [{"effort": "high"}]},
        {"slug": "hidden-model", "visibility": "hide", "supported_reasoning_levels": [{"effort": "high"}]},
    ]}), encoding="utf-8")


def test_codex_models_come_from_local_cache(tmp_path):
    assert codex_models(tmp_path / "none") == {"gpt-5.6-sol": ["xhigh"]}  # 목록이 없으면 기본값만
    write_codex_cache(tmp_path)
    assert codex_models(tmp_path) == {"gpt-5.6-sol": ["low", "xhigh", "ultra"], "gpt-5.5": ["high"]}


def test_yor_catalog_replacement_explains_missing_model_and_recovers(client, tmp_path):
    service = client.app.state.services.agent_settings
    service._codex_home = tmp_path
    cache = tmp_path / "models_cache.json"
    modern = {"models": [{"slug": "gpt-6.1-sol", "visibility": "list",
                          "supported_reasoning_levels": [{"effort": "xhigh"}]}]}
    cache.write_text(json.dumps(modern), encoding="utf-8")
    config = {"provider": "openai", "modelId": "gpt-6.1-sol", "reasoningLevel": "xhigh"}
    assert "gpt-6.1-sol" in by_agent(client.get("/api/settings/agents").json())["yor"]["modelIds"]
    write_codex_cache(tmp_path)  # 사용량 조회 중 구형 CLI가 최신 캐시를 덮어쓴 상황
    failed = client.patch("/api/settings/agents/yor", json=config)
    assert failed.status_code == 400 and "CLI를 업데이트" in failed.json()["detail"]["message"]
    cache.write_text(json.dumps(modern), encoding="utf-8")
    saved = client.patch("/api/settings/agents/yor", json=config)
    assert saved.status_code == 200 and by_agent(saved.json())["yor"]["config"] == config
    failed = client.patch("/api/settings/agents/yor", json={**config, "reasoningLevel": "low"})
    assert failed.status_code == 400 and "지원 값: xhigh" in failed.json()["detail"]["message"]


def test_yor_accepts_only_listed_model_and_effort(settings, tmp_path):
    write_codex_cache(tmp_path / "codex")
    from .conftest import owner_client
    with owner_client(replace(settings, codex_home=tmp_path / "codex")) as client:
        ok = client.patch("/api/settings/agents/yor",
                          json={"provider": "openai", "modelId": "gpt-5.5", "reasoningLevel": "high"})
        assert ok.status_code == 200
        yor = by_agent(ok.json())["yor"]
        assert yor["reasoningByModel"]["gpt-5.6-sol"] == ["low", "xhigh", "ultra"]
        wrong = client.patch("/api/settings/agents/yor",
                             json={"provider": "openai", "modelId": "gpt-5.5", "reasoningLevel": "xhigh"})
        assert wrong.status_code == 400
        assert client.patch("/api/settings/agents/yor",
                            json={"provider": "openai", "modelId": "hidden-model", "reasoningLevel": "high"}).status_code == 400


def test_models_file_is_written_for_the_orchestrator(client, settings):
    client.patch("/api/settings/agents/yuri",
                 json={"provider": "anthropic", "modelId": "claude-haiku-4-5", "reasoningLevel": None})
    client.patch("/api/settings/agents/anya",
                 json={"provider": "anthropic", "modelId": "claude-fable-5-1", "reasoningLevel": None})
    project_id = create_project(client)
    start(client, project_id, "보고서")
    pending_prompt(client, project_id)
    files = list(settings.log_dir.glob("*_models.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8")) == {
        "yor": {"model": "gpt-5.6-sol", "effort": "xhigh"}, "yuri": {"model": "haiku"}, "anya": {"model": "fable"}}


def test_mismatched_calls_in_run_log_are_reported(tmp_path):
    expected = orchestrator_models({"yor": {"modelId": "gpt-6-astra", "reasoningLevel": "high"},
                                    "yuri": {"modelId": "claude-sonnet-5-5"}, "anya": {"modelId": "claude-opus-5-5"}})

    def tool(name: str, data: dict) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": data}]}})

    log = tmp_path / "run.jsonl"
    log.write_text(chr(10).join([
        tool("Agent", {"model": "sonnet", "prompt": "유리 verification"}),
        tool("Bash", {"command": "cat a | codex.cmd exec -m gpt-6-astra -c model_reasoning_effort=high -o x -"}),
    ]), encoding="utf-8")
    assert check_model_calls(log, expected) == []

    log.write_text(chr(10).join([
        tool("Agent", {"model": "sonnet", "prompt": "유리 verification"}),
        tool("Agent", {"model": "opus", "prompt": "아냐 07_final_document"}),
        tool("Bash", {"command": "YM=gpt-6-astra; YE=high; codex.cmd exec -m $YM -c model_reasoning_effort=$YE -o x -"}),
    ]), encoding="utf-8")
    assert check_model_calls(log, expected) == []

    log.write_text(chr(10).join([
        tool("Agent", {"model": "haiku", "prompt": "x"}),
        tool("Bash", {"command": "codex.cmd exec resume abc -m gpt-5.6-sol -c model_reasoning_effort=xhigh -"}),
    ]), encoding="utf-8")
    problems = check_model_calls(log, expected)
    assert len(problems) == 3 and "haiku" in problems[0] and "gpt-5.6-sol" in problems[1] and "xhigh" in problems[2]


def test_system_events_with_string_message_do_not_crash_model_check(tmp_path):
    """permission_denied 같은 system 이벤트는 message가 문자열이다 — 실행을 실패로 닫으면 안 된다."""
    expected = orchestrator_models({"yor": {"modelId": "gpt-6-astra", "reasoningLevel": "high"},
                                    "yuri": {"modelId": "claude-sonnet-5-5"}, "anya": {"modelId": "claude-opus-5-5"}})
    log = tmp_path / "run.jsonl"
    log.write_text(json.dumps({"type": "system", "subtype": "permission_denied", "message": "classifier gave no verdict"}),
                   encoding="utf-8")
    assert check_model_calls(log, expected) == []


def test_model_check_ignores_help_and_accepts_current_snapshot_variables(tmp_path):
    expected = {"yor": {"model": "gpt-5.6-sol", "effort": "medium"},
                "yuri": {"model": "sonnet"}, "anya": {"model": "opus"}}

    def tool(command: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [{
            "type": "tool_use", "name": "Bash", "input": {"command": command}}]}})

    log = tmp_path / "run_abc.jsonl"
    dynamic_call = (
        "YM=$(node -e \"console.log(JSON.parse(require('fs').readFileSync("
        "'run_abc_models.json','utf8')).yor.model)\"); "
        "YE=$(node -e \"console.log(JSON.parse(require('fs').readFileSync("
        "'run_abc_models.json','utf8')).yor.effort)\"); "
        "codex.cmd exec -m \"$YM\" -c model_reasoning_effort=\"$YE\" -o out -"
    )
    log.write_text(chr(10).join([
        tool(dynamic_call),
        tool("codex.cmd exec --help"),
        tool("codex exec -h"),
    ]), encoding="utf-8")

    assert check_model_calls(log, expected) == []


def test_model_check_rejects_variables_from_a_different_snapshot(tmp_path):
    expected = {"yor": {"model": "gpt-5.6-sol", "effort": "medium"},
                "yuri": {"model": "sonnet"}, "anya": {"model": "opus"}}
    command = (
        "YM=$(node -e \"console.log(JSON.parse(require('fs').readFileSync("
        "'old_models.json','utf8')).yor.model)\"); "
        "YE=$(node -e \"console.log(JSON.parse(require('fs').readFileSync("
        "'old_models.json','utf8')).yor.effort)\"); "
        "codex.cmd exec -m \"$YM\" -c model_reasoning_effort=\"$YE\" -"
    )
    log = tmp_path / "run_abc.jsonl"
    log.write_text(json.dumps({"type": "assistant", "message": {"content": [{
        "type": "tool_use", "name": "Bash", "input": {"command": command}}]}}), encoding="utf-8")

    problems = check_model_calls(log, expected)
    assert len(problems) == 2
    assert all("미지정" in problem for problem in problems)


def test_real_run_prompt_marks_snapshot_as_authoritative(settings, monkeypatch, tmp_path):
    """실제 로이드가 임시 경로 이름만 보고 현재 실행 설정을 버리지 않는다."""
    from app import runs as runs_module
    from .conftest import owner_client

    captured = {}

    class CapturingTurn:
        def __init__(self, command, request, on_activity=None):
            captured["prompt"] = request.prompt
            raise OSError("stop after capture")

    monkeypatch.setattr(runs_module, "ProcessTurn", CapturingTurn)
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    (codex_home / "models_cache.json").write_text(json.dumps({"models": [{
        "slug": "gpt-5.6-sol", "visibility": "list",
        "supported_reasoning_levels": [{"effort": "medium"}],
    }]}), encoding="utf-8")
    real_settings = replace(settings, orchestrator="claude", data_dir=tmp_path / "smoke-named-data",
                            codex_home=codex_home)
    with owner_client(real_settings) as client:
        response = client.patch("/api/settings/agents/yor", json={
            "provider": "openai", "modelId": "gpt-5.6-sol", "reasoningLevel": "medium"})
        assert response.status_code == 200
        project_id = create_project(client)
        start(client, project_id, "작은 보고서")
        wait_until(lambda: "웹앱 실행 계약" in captured.get("prompt", ""))

    assert "reasoning=medium" in captured["prompt"]
    assert "yor.py <종류> --id" in captured["prompt"]
    assert "smoke-named-data" in captured["prompt"]
    assert "무시하거나 기본값으로 대체하지 않는다" in captured["prompt"]
    assert "이 프로젝트에 배정된 작업 ID:" in captured["prompt"]
    assert "다른 작업 ID의 상태·파일·최종본을 탐색하거나 이어받거나 완료 근거로 삼지 않는다" in captured["prompt"]


def test_model_mismatch_fails_instead_of_completing(client, monkeypatch):
    from app import runs as runs_module

    monkeypatch.setattr(runs_module, "check_model_calls",
                        lambda log_path, expected: ["요르 추론 강도가 설정과 다릅니다."])
    project_id = create_project(client)
    start(client, project_id, "작은 보고서")

    def terminal_events():
        events = client.get(f"/api/projects/{project_id}/workspace").json()["events"]
        return [event for event in events if event["type"] in {"workflow.failed", "workflow.completed"}]

    terminal = wait_until(terminal_events)
    assert terminal[-1]["type"] == "workflow.failed"
    assert "홈페이지 설정과 달라" in terminal[-1]["reason"]


def test_subagent_model_does_not_silently_fallback():
    with pytest.raises(UnsupportedConfigError):
        orchestrator_models({"anya": {"modelId": "removed-model"}})
