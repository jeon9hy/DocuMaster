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
