"""SSE: afterSeq replay · Last-Event-ID 재연결 · 실시간 전달을 실제 서버로 확인한다."""

import json
import threading

import httpx

from .conftest import wait_until


def read_events(url: str, count: int, headers: dict | None = None, timeout: float = 10) -> list[dict]:
    received: list[dict] = []
    with httpx.stream("GET", url, headers=headers or {}, timeout=timeout) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("data: "):
                received.append(json.loads(line[6:]))
                if len(received) >= count:
                    break
    return received


def test_replay_after_seq_then_live_event(live_server, owner_http):
    base = live_server.url + "/api/projects"
    project_id = owner_http.post(base, json={"name": "SSE", "mode": "auto"}).json()["id"]
    for text in ("1", "2", "3"):
        owner_http.post(f"{base}/{project_id}/messages", json={"text": text})

    result: list[dict] = []
    reader = threading.Thread(target=lambda: result.extend(read_events(f"{base}/{project_id}/events?afterSeq=1", 3)))
    reader.start()
    wait_until(lambda: True)  # 구독 시작 여유
    owner_http.post(f"{base}/{project_id}/messages", json={"text": "실시간"})
    reader.join(timeout=10)
    assert [event["seq"] for event in result] == [2, 3, 4]
    assert result[-1]["text"] == "실시간"


def test_reconnect_with_last_event_id_skips_already_received(live_server, owner_http):
    base = live_server.url + "/api/projects"
    project_id = owner_http.post(base, json={"name": "SSE", "mode": "auto"}).json()["id"]
    for text in ("a", "b", "c", "d"):
        owner_http.post(f"{base}/{project_id}/messages", json={"text": text})
    # 브라우저 EventSource가 자동 재연결 때 보내는 헤더. URL의 afterSeq보다 우선한다.
    events = read_events(f"{base}/{project_id}/events?afterSeq=0", 2, headers={"Last-Event-ID": "2"})
    assert [event["seq"] for event in events] == [3, 4]


def test_unknown_project_stream_is_404(live_server):
    assert httpx.get(live_server.url + "/api/projects/nope/events").status_code == 404
