"""요르(Codex) 진행을 대화 피드로 옮긴다.

요르는 로이드가 셸로 부르는 `.claude/tools/yor.py`라 Claude stream-json에 말이 실리지 않는다.
대신 yor.py가 남기는 두 파일을 읽기만 한다(모델을 부르지 않는다).
- `작업/<ID>/_yor_call.json` — 지금 호출의 상태(running/done)·종류·로그 경로·시작 시각
- 그 로그(`_log_02.txt` 등) — `codex exec`의 사람용 출력. 블록 머리 줄로 나뉜다:
  `user`(붙여 보낸 입력 — 보여 주지 않는다) · `codex`(요르의 중간 보고 — 대화로) ·
  `web search: …`(검색 — 검색어는 숨기고 건수만) · `exec`(명령 — 건수만) · `thinking`·`tokens used`(무시)
마지막 `codex` 블록은 산출물 전문이라 대화에 싣지 않는다(작업물 카드로 따로 보인다).
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

CALL_LABELS = {"research": "조사 02", "answer": "검증 응답 04", "plan": "PPT 세부 기획 06",
               "pack": "PPT 발표팩 07", "patch": "수정 PATCH"}
# 산출물 전문(대화에 싣지 않는다): 제목으로 시작하거나 헤더 구분선이 있거나 아주 길다
_FINAL_MARKERS = ("--- 헤더 끝 ---", "=== 수정 패치 시작 ===")
_MAX_MESSAGE = 1200
_BLOCK_HEADS = {"user", "codex", "exec", "thinking", "tokens used"}
COUNT_FLUSH_SECONDS = 20  # 검색만 길게 이어질 때도 요르가 살아 있는 게 보이게, 이 간격으로 건수를 올린다


def _is_final(text: str) -> bool:
    return text.startswith("#") or len(text) > _MAX_MESSAGE or any(marker in text for marker in _FINAL_MARKERS)


def _started_epoch(value: object) -> float | None:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return None


class YorLogFollower:
    """한 프로젝트의 요르 호출을 따라 읽는다. 새로 본 줄만 이벤트로 바꾼다(같은 줄을 두 번 내지 않는다)."""

    def __init__(self, now: float | None = None):
        self._created = time.time() if now is None else now
        self._call: tuple[str, str] | None = None  # (로그 경로, 시작 시각)
        self._offset = 0
        self._partial = b""
        self._mode = "skip"
        self._lines: list[str] = []
        self._searches = 0
        self._commands = 0
        self._last_flush = 0.0

    def poll(self, work_dir: Path | None) -> list[dict]:
        if work_dir is None:
            return []
        try:
            state = json.loads((work_dir / "_yor_call.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(state, dict):
            return []
        events: list[dict] = []
        running = state.get("status") == "running"
        log_rel = state.get("log")
        key = (str(log_rel), str(state.get("started_at")))
        if running and log_rel and key != self._call:
            events += self._finish_call()
            self._start_call(key, work_dir / str(log_rel), state)
            if self._call is not None:
                label = CALL_LABELS.get(str(state.get("kind")), "작업")
                events.append({"type": "agent.activity", "agentId": "yor", "label": f"{label} 시작"})
        if self._call is None:
            return events
        events += self._read_new(work_dir / self._call[0])
        if not running:
            events += self._finish_call(state)
        elif time.monotonic() - self._last_flush >= COUNT_FLUSH_SECONDS:
            events += self._flush_counts()
        return events

    def _start_call(self, key: tuple[str, str], log: Path, state: dict) -> None:
        self._call, self._partial, self._mode, self._lines = key, b"", "skip", []
        self._searches = self._commands = 0
        self._offset = 0
        started = _started_epoch(state.get("started_at"))
        # 백엔드가 켜지기 전에 시작한 호출은 이미 쓰인 부분을 건너뛴다(재시작 뒤 같은 말이 다시 올라오지 않게)
        if started is not None and started < self._created:
            try:
                self._offset = log.stat().st_size
            except OSError:
                pass

    def _read_new(self, log: Path) -> list[dict]:
        try:
            with log.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except OSError:
            return []
        self._offset += len(chunk)
        data = self._partial + chunk
        lines = data.split(b"\n")
        self._partial = lines.pop()  # 아직 끝나지 않은 줄은 다음에
        events: list[dict] = []
        for raw in lines:
            events += self._line(raw.decode("utf-8", errors="replace").rstrip("\r"))
        return events

    def _line(self, line: str) -> list[dict]:
        head = line.strip()
        if head.startswith("web search:"):
            events = self._flush_message()
            self._mode = "other"
            self._searches += 1
            return events
        if head in _BLOCK_HEADS and line == head:
            events = self._flush_message()
            if head == "exec":
                self._commands += 1
            self._mode = {"codex": "codex", "user": "skip"}.get(head, "other")
            return events
        if self._mode == "codex":
            self._lines.append(line)
        return []

    def _flush_counts(self) -> list[dict]:
        parts = []
        if self._searches:
            parts.append(f"웹 검색 {self._searches}건")
        if self._commands:
            parts.append(f"명령 실행 {self._commands}건")
        self._searches = self._commands = 0
        self._last_flush = time.monotonic()
        return [{"type": "agent.activity", "agentId": "yor", "label": " · ".join(parts)}] if parts else []

    def _flush_message(self) -> list[dict]:
        text = "\n".join(self._lines).strip()
        self._lines = []
        if not text:
            return []
        events = self._flush_counts()
        if _is_final(text):
            events.append({"type": "agent.activity", "agentId": "yor", "label": "결과 정리"})
        else:
            events.append({"type": "agent.message", "agentId": "yor", "text": text})
        return events

    def _finish_call(self, state: dict | None = None) -> list[dict]:
        if self._call is None:
            return []
        if self._partial:
            events = self._line(self._partial.decode("utf-8", errors="replace").rstrip("\r"))
            self._partial = b""
        else:
            events = []
        events += self._flush_message() + self._flush_counts()
        if state is not None:
            label = CALL_LABELS.get(str(state.get("kind")), "작업")
            done = state.get("status") == "done" and state.get("exit") == 0
            events.append({"type": "agent.activity", "agentId": "yor", "label": f"{label} {'끝' if done else '중단'}"})
        self._call = None
        return events
