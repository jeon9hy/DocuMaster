"""모델 사용량 — **실제로 확인되는 값만** 돌려준다. 추정·계산·가짜 값을 만들지 않는다.

- Codex: Codex CLI의 공식 app-server 프로토콜 `account/rateLimits/read`로 계정의 현재 한도를 바로 읽는다
  (모델을 부르지 않는다). 계정에는 한도가 여러 개라 `codex` 한도(5시간·주간)만 쓴다. 못 읽으면 확인 불가.
- Claude Code: 공식 statusLine이 넘기는 rate_limits를 server/claude_statusline.py가 .data/claude_usage.json에 남긴다.
  Claude Code 대화에서 응답을 받을 때마다 갱신된다. 리셋 시각이 지난 창은 값이 끝난 것이라 「오래됨」으로 표시한다.
- NotebookLM: 사용량 인터페이스가 없다 → 확인 불가.
인증 정보(토큰·키)는 읽지 않는다.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

CODEX_TIMEOUT_SECONDS = 15
CODEX_CACHE_SECONDS = 30  # 화면을 열 때마다 프로세스를 띄우지 않게 잠깐 기억한다
CODEX_LIMIT_ID = "codex"
FIVE_HOURS, ONE_WEEK = 300, 10080

_codex_cache: tuple[float, dict] | None = None
_codex_lock = threading.Lock()


def _iso(epoch: float | int | None) -> str | None:
    if not isinstance(epoch, (int, float)):
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _unavailable(provider: str, label: str, note: str, source: str | None = None) -> dict:
    return {"provider": provider, "label": label, "available": False, "stale": False, "windows": [],
            "observedAt": None, "source": source, "note": note}


# --- Codex -------------------------------------------------------------------------


def _codex_rpc() -> dict:
    """codex app-server를 잠깐 띄워 initialize → account/rateLimits/read 한 번만 주고받는다."""
    executable = shutil.which("codex")
    if not executable:
        raise RuntimeError("codex CLI를 찾을 수 없습니다.")
    process = subprocess.Popen([executable, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    result: dict = {}
    done = threading.Event()

    def read() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == 2:
                result.update(message)
                done.set()
                return

    threading.Thread(target=read, daemon=True).start()
    try:
        assert process.stdin is not None
        for message in ({"id": 1, "method": "initialize",
                         "params": {"clientInfo": {"name": "documaster", "version": "0.1.0"}}},
                        {"method": "initialized"},
                        {"id": 2, "method": "account/rateLimits/read"}):
            process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
            process.stdin.flush()
        if not done.wait(CODEX_TIMEOUT_SECONDS):
            raise RuntimeError("Codex 응답 시간 초과")
    finally:
        process.kill()
    if "error" in result:
        raise RuntimeError(str(result["error"].get("message") if isinstance(result["error"], dict) else result["error"]))
    return result.get("result") or {}


def codex_usage_from(response: dict) -> dict:
    label = "OpenAI · Codex"
    limits = (response.get("rateLimitsByLimitId") or {}).get(CODEX_LIMIT_ID) or response.get("rateLimits")
    if not isinstance(limits, dict) or limits.get("limitId", CODEX_LIMIT_ID) != CODEX_LIMIT_ID:
        return _unavailable("openai", label, "Codex 계정에서 사용량 정보를 받지 못했습니다.")
    windows = []
    for key in ("primary", "secondary"):
        window = limits.get(key)
        if isinstance(window, dict) and isinstance(window.get("usedPercent"), (int, float)):
            windows.append({"kind": key, "usedPercent": float(window["usedPercent"]),
                            "windowMinutes": window.get("windowDurationMins"),
                            "resetsAt": _iso(window.get("resetsAt"))})
    if not windows:
        return _unavailable("openai", label, "Codex 계정에서 사용량 정보를 받지 못했습니다.")
    return {"provider": "openai", "label": label, "available": True, "stale": False, "windows": windows,
            "observedAt": _now_iso(), "plan": limits.get("planType"), "limitReached": limits.get("rateLimitReachedType"),
            "source": "Codex CLI (account/rateLimits/read)", "note": "Codex 계정의 현재 값입니다."}


def codex_usage(fetch=_codex_rpc) -> dict:
    global _codex_cache
    with _codex_lock:
        if _codex_cache and time.monotonic() - _codex_cache[0] < CODEX_CACHE_SECONDS:
            return _codex_cache[1]
        try:
            usage = codex_usage_from(fetch())
        except (OSError, RuntimeError, ValueError) as error:
            log.warning("Codex 사용량 조회 실패: %s", error)
            return _unavailable("openai", "OpenAI · Codex",
                                f"Codex 사용량을 읽지 못했습니다({error}). Codex 로그인 상태를 확인하세요.")
        _codex_cache = (time.monotonic(), usage)
        return usage


# --- Claude Code ---------------------------------------------------------------------


CLAUDE_WINDOWS = (("five_hour", FIVE_HOURS), ("seven_day", ONE_WEEK))


def claude_usage(cache: Path, now: float | None = None) -> dict:
    label = "Anthropic · Claude Code"
    source = "Claude Code statusLine"
    now = time.time() if now is None else now
    if not cache.exists():
        return _unavailable("anthropic", label,
                            "Claude Code 사용량 정보를 아직 받지 못했습니다. 터미널에서 Claude Code로 메시지를 한 번 보낸 뒤 새로고침하세요.",
                            source)
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("객체가 아님")
    except (OSError, ValueError) as error:
        log.warning("Claude 사용량 캐시를 읽지 못했습니다: %s", error)
        return _unavailable("anthropic", label, "Claude 사용량 캐시가 손상되었습니다. Claude Code를 한 번 더 쓰면 다시 만들어집니다.",
                            source)
    windows = []
    stale = False
    for key, minutes in CLAUDE_WINDOWS:
        window = data.get(key)
        if not isinstance(window, dict) or not isinstance(window.get("used_percentage"), (int, float)):
            continue
        resets_at = window.get("resets_at")
        # 리셋 시각이 지났으면 그 값은 끝난 창의 값이다 — 지금 값처럼 보이지 않게 표시한다
        expired = isinstance(resets_at, (int, float)) and resets_at <= now
        stale = stale or expired
        windows.append({"kind": key, "usedPercent": float(window["used_percentage"]), "windowMinutes": minutes,
                        "resetsAt": _iso(resets_at), "expired": expired})
    if not windows:
        return _unavailable("anthropic", label, "Claude 사용량 캐시에 한도 정보가 없습니다.", source)
    note = ("리셋이 지난 한도가 있습니다. Claude Code를 다시 쓰면 새 값으로 바뀝니다." if stale
            else "Claude Code에서 마지막으로 응답을 받았을 때의 값입니다.")
    return {"provider": "anthropic", "label": label, "available": True, "stale": stale, "windows": windows,
            "observedAt": data.get("captured_at"), "source": source, "note": note}


def usage_report(claude_cache: Path, codex_live: bool = True) -> list[dict]:
    return [
        claude_usage(claude_cache),
        codex_usage() if codex_live else _unavailable("openai", "OpenAI · Codex", "Codex 실시간 조회를 끈 상태입니다."),
        _unavailable("google", "Google · NotebookLM", "사용량 정보를 제공하지 않습니다. Provider에서 직접 확인하세요."),
    ]
