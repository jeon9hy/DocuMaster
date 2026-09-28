import json

from app.yor_feed import YorLogFollower

HEADER = """OpenAI Codex v0.154.0
--------
model: gpt-5.6-sol
--------
user
# 요르 — 조사·기획 담당
붙여 보낸 입력은 대화에 올리지 않는다.
codex
"""


def call_state(work_dir, status, started="2026-09-27T22:10:00+09:00", exit_code=None):
    state = {"status": status, "kind": "research", "log": "_log_02.txt", "started_at": started}
    if exit_code is not None:
        state["exit"] = exit_code
    (work_dir / "_yor_call.json").write_text(json.dumps(state), encoding="utf-8")


def test_follows_codex_messages_and_counts_searches(tmp_path):
    log = tmp_path / "_log_02.txt"
    log.write_text(HEADER + "웹 원문을 직접 열어 확인하겠습니다.\nweb search: \nweb search: site:x.org 질의\n",
                   encoding="utf-8")
    call_state(tmp_path, "running")
    follower = YorLogFollower(now=0)

    first = follower.poll(tmp_path)
    assert first[0] == {"type": "agent.activity", "agentId": "yor", "label": "조사 02 시작"}
    assert {"type": "agent.message", "agentId": "yor", "text": "웹 원문을 직접 열어 확인하겠습니다."} in first
    assert not any("붙여 보낸" in json.dumps(event, ensure_ascii=False) for event in first)
    assert not any("site:x.org" in json.dumps(event, ensure_ascii=False) for event in first)  # 검색어는 숨긴다
    assert follower.poll(tmp_path) == []  # 같은 줄을 두 번 내지 않는다

    with log.open("a", encoding="utf-8") as handle:
        handle.write("codex\n중간 보고입니다.\ncodex\n# Research Pack\n--- 헤더 끝 ---\n본문\n")
    call_state(tmp_path, "done", exit_code=0)
    rest = follower.poll(tmp_path)
    labels = [event.get("label") or event.get("text") for event in rest]
    assert labels == ["웹 검색 2건", "중간 보고입니다.", "결과 정리", "조사 02 끝"]


def test_call_started_before_backend_skips_old_lines(tmp_path):
    (tmp_path / "_log_02.txt").write_text(HEADER + "예전 보고\nweb search: \n", encoding="utf-8")
    call_state(tmp_path, "running", started="2026-09-27T22:10:00+09:00")
    follower = YorLogFollower(now=4_000_000_000)  # 백엔드가 호출보다 나중에 켜졌다
    events = follower.poll(tmp_path)
    assert [event["label"] for event in events] == ["조사 02 시작"]


def test_no_call_file_means_nothing(tmp_path):
    assert YorLogFollower().poll(tmp_path) == []
    assert YorLogFollower().poll(None) == []


def test_follows_json_events_and_shows_opened_sites(tmp_path):
    """--json 이벤트 로그: 중간 보고는 대화로, 연 페이지는 도메인만, 검색·명령은 건수만, 모르는 이벤트는 건너뛴다."""
    events_log = tmp_path / "_log_02.jsonl"
    lines = [
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "item.completed", "item": {"type": "reasoning", "text": "숨긴다"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "원문을 열어 보겠습니다."}},
        {"type": "item.completed", "item": {"type": "web_search", "query": "비밀 검색어",
                                            "action": {"type": "search", "queries": ["a", "b"]}}},
        {"type": "item.completed", "item": {"type": "web_search",
                                            "action": {"type": "open_page", "url": "https://www.krivet.re.kr/x.pdf"}}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "rm -rf 숨김"}},
        {"type": "future.event", "anything": 1},
        "not json",
    ]
    events_log.write_text("\n".join(json.dumps(line, ensure_ascii=False) if isinstance(line, dict) else line
                                    for line in lines) + "\n", encoding="utf-8")
    state = {"status": "running", "kind": "research", "log": "_log_02.txt", "events": "_log_02.jsonl",
             "started_at": "2026-09-27T22:10:00+09:00"}
    (tmp_path / "_yor_call.json").write_text(json.dumps(state), encoding="utf-8")
    follower = YorLogFollower(now=0)
    got = follower.poll(tmp_path)
    labels = [event.get("label") or event.get("text") for event in got]
    assert labels == ["조사 02 시작", "원문을 열어 보겠습니다.", "웹 검색 2건", "웹 자료 열기 · www.krivet.re.kr"]
    dumped = json.dumps(got, ensure_ascii=False)
    assert "비밀 검색어" not in dumped and "숨김" not in dumped and "숨긴다" not in dumped

    with events_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "item.completed", "item": {
            "type": "agent_message", "text": "# Research Pack\n--- 헤더 끝 ---\n본문"}}, ensure_ascii=False) + "\n")
    (tmp_path / "_yor_call.json").write_text(json.dumps({**state, "status": "done", "exit": 0}), encoding="utf-8")
    rest = [event.get("label") or event.get("text") for event in follower.poll(tmp_path)]
    assert rest == ["명령 실행 1건", "결과 정리", "조사 02 끝"]
