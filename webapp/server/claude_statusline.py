"""Claude Code statusLine 명령 — 상태 표시줄을 출력하고, 받은 rate_limits만 DocuMaster 캐시에 남긴다.

Claude Code가 세션 정보를 JSON으로 stdin에 넘긴다(공식 문서: code.claude.com/docs/en/statusline).
- 캐시: webapp/.data/claude_usage.json — 사용 %와 리셋 시각만. 인증 정보는 읽지도 쓰지도 않는다.
- rate_limits가 없으면(첫 응답 전·해당 요금제 아님) 캐시를 건드리지 않는다. 창(five_hour·seven_day)은 따로 갱신한다.
- 쓰기는 임시 파일 → 교체(os.replace)라 백엔드가 읽다가 깨진 JSON을 보지 않는다.
- 무슨 일이 있어도 상태 표시줄 한 줄은 출력하고 0으로 끝난다(Claude Code 화면을 깨지 않는다).
표준 라이브러리만 쓴다.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# 테스트만 다른 곳에 쓰도록 바꿀 수 있다(실제 캐시를 더럽히지 않게)
CACHE = Path(os.environ.get("DOCUMASTER_CLAUDE_USAGE_CACHE")
             or Path(__file__).resolve().parents[1] / ".data" / "claude_usage.json")
WINDOWS = ("five_hour", "seven_day")


def _window(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    used, resets = raw.get("used_percentage"), raw.get("resets_at")
    if not isinstance(used, (int, float)) or not isinstance(resets, (int, float)):
        return None
    return {"used_percentage": float(used), "resets_at": int(resets)}


def save(data: dict, cache: Path | None = None) -> bool:
    cache = cache or CACHE  # 부를 때 읽는다(테스트가 CACHE를 바꿀 수 있게)
    limits = data.get("rate_limits")
    if not isinstance(limits, dict):
        return False
    windows = {name: _window(limits.get(name)) for name in WINDOWS}
    windows = {name: value for name, value in windows.items() if value}
    if not windows:
        return False
    try:
        previous = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    record = {"source": "claude-code-statusline", "captured_at": now}
    for name in WINDOWS:
        if name in windows:
            record[name] = {**windows[name], "captured_at": now}
        elif isinstance(previous.get(name), dict):
            record[name] = previous[name]  # 이번에 빠진 창은 이전 값을 두고, 오래됐는지는 백엔드가 판단한다
    cache.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=cache.parent, prefix=".claude_usage.", suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        json.dump(record, file)
    os.replace(temp, cache)
    return True


def status_text(data: dict) -> str:
    model = ((data.get("model") or {}).get("display_name")) or "Claude"
    parts = [f"[{model}]"]
    context = (data.get("context_window") or {}).get("used_percentage")
    if isinstance(context, (int, float)):
        parts.append(f"ctx {context:.0f}%")
    limits = data.get("rate_limits") or {}
    for name, label in (("five_hour", "5h"), ("seven_day", "7d")):
        window = _window(limits.get(name)) if isinstance(limits, dict) else None
        if window:
            parts.append(f"{label} {window['used_percentage']:.0f}%")
    return " · ".join(parts)


def main() -> int:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
        if not isinstance(data, dict):
            data = {}
    except ValueError:
        data = {}
    try:
        save(data)
    except OSError:
        pass  # 캐시를 못 써도 상태 표시줄은 보여 준다
    sys.stdout.buffer.write(status_text(data).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
