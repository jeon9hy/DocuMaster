"""기존 CLI 로그의 공개 가능한 발언·활동을 실행 중 화면에 전달한다."""

import json
import sys
import threading
from pathlib import Path

from app.orchestrator import ProcessTurn, StreamActivity, TurnRequest
from .conftest import create_project, events_of, wait_until


def _assistant(blocks, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"role": "assistant", "content": blocks}}


def test_stream_activity_uses_only_actual_text_and_labels_tools_safely():
    reader = StreamActivity()
    assert reader.read(_assistant([{"type": "thinking", "thinking": "비공개 내용"}])) == []
    events = reader.read(_assistant([
        {"type": "text", "text": "자료를 확인하겠습니다."},
        {"type": "tool_use", "name": "Bash", "input": {"command": "secret --token=123"}},
        {"type": "tool_use", "name": "Agent", "id": "agent-1",
         "input": {"description": "유리 03 검증 질문", "prompt": "비공개 지시"}},
    ]))
    assert events == [
        {"type": "agent.message", "agentId": "loid", "text": "자료를 확인하겠습니다."},
        {"type": "agent.activity", "agentId": "loid", "label": "하위 에이전트 작업 요청 · 유리"},
    ]
    assert reader.read(_assistant([{"type": "text", "text": "수치를 다시 확인해야 합니다."}], "agent-1")) == [
        {"type": "agent.message", "agentId": "yuri", "text": "수치를 다시 확인해야 합니다."},
    ]
    reader.read({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "agent-1", "content": [
            {"type": "text", "text": "agentId: internal123 (internal ID)"},
        ]},
    ]}})
    assert reader.read(_assistant([{"type": "tool_use", "name": "SendMessage",
                                   "input": {"recipient": "internal123", "content": "원문을 다시 확인해 주세요."}}])) == [
        {"type": "agent.message", "agentId": "loid", "toAgentId": "yuri",
         "text": "원문을 다시 확인해 주세요."},
    ]
    assert reader.read(_assistant([{"type": "text", "text": "역할을 모릅니다."}], "unknown")) == []
    assert "secret" not in json.dumps(events, ensure_ascii=False)


def test_process_turn_forwards_activity_before_result(tmp_path: Path):
    script = tmp_path / "stream.py"
    script.write_text(
        "import json,sys,time\n"
        "print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'진행 중입니다.'}]}}), flush=True)\n"
        "time.sleep(0.35)\n"
        "print(json.dumps({'type':'result','result':'완료했습니다.','is_error':False}), flush=True)\n",
        encoding="utf-8",
    )
    request = TurnRequest(prompt="테스트", session_id="test", resume=False, work_root=tmp_path,
                          log_path=tmp_path / "run.jsonl")
    received = threading.Event()
    events = []

    def on_activity(event):
        events.append(event)
        received.set()

    process = ProcessTurn([sys.executable, str(script)], request, on_activity=on_activity)
    assert received.wait(timeout=2)
    assert process.is_alive()
    assert events == [{"type": "agent.message", "agentId": "loid", "text": "진행 중입니다."}]
    assert process.wait().result_text == "완료했습니다."
    assert process.already_streamed("진행 중입니다.")


def test_live_message_reaches_project_events_while_process_runs(client, tmp_path: Path):
    script = tmp_path / "live.py"
    script.write_text(
        "import json,time\n"
        "print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'실시간 보고'}]}}), flush=True)\n"
        "time.sleep(1)\n"
        "print(json.dumps({'type':'result','result':'끝','is_error':False}), flush=True)\n",
        encoding="utf-8",
    )

    class ScriptAdapter:
        def missing_tools(self):
            return []

        def build_command(self, request):
            return [sys.executable, str(script)]

    project_id = create_project(client)
    client.app.state.services.runs._adapter = ScriptAdapter()
    assert client.post(f"/api/projects/{project_id}/messages", json={"text": "실시간 테스트"}).status_code == 201
    assert client.post(f"/api/projects/{project_id}/runs").status_code == 202
    message = wait_until(lambda: next((event for event in events_of(client, project_id)
                                       if event["type"] == "agent.message"), None))
    assert message["text"] == "실시간 보고"
    assert client.app.state.services.runs._turn.process.is_alive()
