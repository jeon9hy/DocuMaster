"""모델 사용량 — **실제로 확인되는 값만** 돌려준다. 추정·계산·가짜 값을 만들지 않는다.

- Codex: Codex CLI의 공식 app-server 프로토콜 `account/rateLimits/read`로 계정의 현재 한도를 바로 읽는다
  (모델을 부르지 않는다). 계정에는 한도가 여러 개라 `codex` 한도(5시간·주간)만 쓴다. 못 읽으면 확인 불가.
- Claude Code: Codex 같은 공식 한도 조회 명령이 없다. 대신 Claude가 **응답마다 보내는 rate_limit_event**를 받는다.
  실시간 값은 가장 싼 호출(haiku, 도구·설정·세션 저장 없음, 첫 이벤트를 받으면 바로 끊음)로 읽는다 — 1회 약 $0.002.
  **실행 중에는** 그 실행 로그에 방금 들어온 값을 쓰고 조회 호출을 하지 않는다.
  그 호출이 실패하면 statusLine 캐시(server/claude_statusline.py → .data/claude_usage.json)와
  웹앱 실행 로그 중 **더 최근 값**을 쓴다. 리셋 시각이 지난 창은 「오래됨」으로 표시한다.
- NotebookLM: 사용량 인터페이스가 없어 보여 주지 않는다.
인증 정보(토큰·키)는 읽지 않는다.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

CODEX_TIMEOUT_SECONDS = 15
CODEX_CACHE_SECONDS = 30  # 화면을 열 때마다 프로세스를 띄우지 않게 잠깐 기억한다
CLAUDE_TIMEOUT_SECONDS = 20  # 로그인이 풀려 응답이 없으면 화면이 오래 기다리지 않게
CLAUDE_CACHE_SECONDS = 60  # 실시간 조회는 작은 호출 한 번이라 Codex보다 길게 기억한다
ACTIVE_LOG_SECONDS = 180  # 실행 로그가 이 안에 쓰였으면 실행 중으로 보고 그 값을 쓴다
CODEX_LIMIT_ID = "codex"
FIVE_HOURS, ONE_WEEK = 300, 10080

_codex_cache: tuple[float, dict] | None = None
_codex_lock = threading.Lock()
_claude_cache: tuple[float, dict] | None = None
_claude_lock = threading.Lock()


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


def _claude_windows(info: dict, now: float) -> list[dict]:
    """rate_limit_event의 unifiedWindows → 화면용 창 목록. 형식이 맞지 않는 창은 버린다."""
    unified = info.get("unifiedWindows")
    windows: list[dict] = []
    if not isinstance(unified, dict):
        return windows
    for key, minutes in CLAUDE_WINDOWS:
        raw = unified.get(key)
        if not isinstance(raw, dict):
            continue
        utilization, resets_at = raw.get("utilization"), raw.get("resetsAt")
        if (not isinstance(utilization, (int, float)) or isinstance(utilization, bool)
                or not isinstance(resets_at, (int, float)) or isinstance(resets_at, bool)
                or not 0 <= utilization <= 1):
            continue
        windows.append({"kind": key, "usedPercent": round(utilization * 100, 2),
                        "windowMinutes": minutes, "resetsAt": _iso(resets_at),
                        "expired": resets_at <= now})
    return windows


def _last_rate_limit_info(path: Path) -> dict | None:
    """로그 파일의 마지막 rate_limit_event 한도 정보."""
    latest = None
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if '"rate_limit_event"' not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            info = event.get("rate_limit_info") if isinstance(event, dict) else None
            if isinstance(info, dict) and isinstance(info.get("unifiedWindows"), dict):
                latest = info
    return latest


def claude_usage_from_active_run(log_dir: Path, now: float | None = None) -> dict | None:
    """진행 중인 실행(최근에 쓰인 로그)의 마지막 한도 값. 실행 중이 아니거나 값이 없으면 None."""
    now = time.time() if now is None else now
    try:
        logs = [path for path in log_dir.glob("run_*.jsonl") if not path.stem.endswith("_telemetry")]
        path = max(logs, key=lambda item: item.stat().st_mtime, default=None)
        if path is None or now - path.stat().st_mtime > ACTIVE_LOG_SECONDS:
            return None
        info = _last_rate_limit_info(path)
        modified_at = path.stat().st_mtime
    except OSError as error:
        log.warning("실행 로그를 읽지 못했습니다: %s", error)
        return None
    windows = _claude_windows(info, now) if info else []
    if not windows:
        return None
    return {"provider": "anthropic", "label": "Anthropic · Claude Code", "available": True,
            "stale": any(window["expired"] for window in windows), "windows": windows,
            "observedAt": _iso(modified_at), "source": "진행 중인 실행 로그 (rate_limit_event)",
            "note": "진행 중인 실행에서 방금 받은 값입니다."}


def claude_usage_from_logs(log_dir: Path, now: float | None = None) -> dict:
    """headless Claude 실행의 실제 rate_limit_event를 읽는다. 모델 호출은 하지 않는다."""
    label = "Anthropic · Claude Code"
    source = "Claude Code 실행 로그 (rate_limit_event)"
    now = time.time() if now is None else now
    latest: tuple[float, dict] | None = None
    # 기존 Phase E 실험은 .data/smoke/logs에 격리해 두었다.
    paths = (*log_dir.glob("run_*.jsonl"), *(log_dir.parent / "smoke" / "logs").glob("run_*.jsonl"))
    stamped = []
    for path in paths:
        try:
            stamped.append((path.stat().st_mtime, path))
        except OSError as error:
            log.warning("Claude 실행 로그를 읽지 못했습니다: %s", error)
    # 실행 하나의 로그가 수 MB다 — 최신 로그부터 보고 값이 있는 첫 로그에서 멈춘다(전부 파싱하지 않는다)
    for modified_at, path in sorted(stamped, key=lambda item: item[0], reverse=True):
        try:
            info = _last_rate_limit_info(path)
        except OSError as error:
            log.warning("Claude 실행 로그를 읽지 못했습니다: %s", error)
            continue
        if info:
            latest = (modified_at, info)
            break
    if latest is None:
        return _unavailable("anthropic", label, "Claude 사용량 정보를 확인할 수 없습니다.", source)
    captured_at, info = latest
    windows = _claude_windows(info, now)
    if not windows:
        return _unavailable("anthropic", label, "Claude 실행 로그에 유효한 한도 정보가 없습니다.", source)
    return {"provider": "anthropic", "label": label, "available": True,
            "stale": any(window["expired"] for window in windows), "windows": windows,
            "observedAt": _iso(captured_at), "source": source,
            "note": "마지막 Claude 실행에서 확인된 값입니다. 현재 값은 다음 실행 전까지 달라질 수 있습니다."}


# 가장 싼 호출: haiku · 도구 없음 · 사용자/프로젝트 설정(훅·statusLine·MCP) 안 읽음 · 세션 저장 안 함.
# 옵션은 `claude --help`(2.1.282)에서 확인한 것만 쓴다.
_PROBE_ARGS = ("-p", ".", "--model", "haiku", "--output-format", "stream-json", "--verbose",
               "--tools", "", "--system-prompt", ".", "--setting-sources", "", "--strict-mcp-config",
               "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence", "--disable-slash-commands",
               "--max-turns", "1")


def _claude_probe() -> dict:
    """claude를 잠깐 띄워 첫 rate_limit_event의 rate_limit_info만 받고 바로 끊는다."""
    executable = shutil.which("claude")
    if not executable:
        raise RuntimeError("claude CLI를 찾을 수 없습니다.")
    # 저장소 밖(임시 폴더)에서 띄워 CLAUDE.md·.claude/를 읽지 않게 한다
    process = subprocess.Popen([executable, *_PROBE_ARGS], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, cwd=tempfile.gettempdir())
    result: dict = {}
    done = threading.Event()

    def read() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "rate_limit_event":
                if isinstance(event.get("rate_limit_info"), dict):
                    result.update(event["rate_limit_info"])
                break
        done.set()

    threading.Thread(target=read, daemon=True).start()
    try:
        if not done.wait(CLAUDE_TIMEOUT_SECONDS):
            raise RuntimeError("Claude 응답 시간 초과")
    finally:
        process.kill()
    if not result:
        raise RuntimeError("Claude가 한도 정보를 보내지 않았습니다. 로그인 상태를 확인하세요.")
    return result


def claude_usage_live(probe=_claude_probe, now: float | None = None) -> dict | None:
    """실시간 값. 실패하면 None — 부른 쪽이 statusLine 캐시·실행 로그로 대신한다."""
    global _claude_cache
    with _claude_lock:
        if _claude_cache and time.monotonic() - _claude_cache[0] < CLAUDE_CACHE_SECONDS:
            return _claude_cache[1]
        try:
            windows = _claude_windows(probe(), time.time() if now is None else now)
        except (OSError, RuntimeError, ValueError) as error:
            log.warning("Claude 사용량 실시간 조회 실패: %s", error)
            return None
        if not windows:
            return None
        usage = {"provider": "anthropic", "label": "Anthropic · Claude Code", "available": True,
                 "stale": any(window["expired"] for window in windows), "windows": windows,
                 "observedAt": _now_iso(), "source": "Claude Code CLI (rate_limit_event)",
                 "note": "Claude 계정의 현재 값입니다."}
        _claude_cache = (time.monotonic(), usage)
        return usage


def _newer(a: dict, b: dict) -> dict:
    """둘 다 확인된 값이면 기준 시각이 늦은 쪽, 하나만 확인됐으면 그쪽."""
    if not a["available"]:
        return b if b["available"] else a
    if not b["available"]:
        return a
    return a if (a.get("observedAt") or "") >= (b.get("observedAt") or "") else b


def usage_report(claude_cache: Path, codex_live: bool = True, claude_log_dir: Path | None = None,
                 claude_live: bool = False) -> list[dict]:
    # 실행 중이면 그 로그에 한도 값이 계속 들어온다 — Claude 조회 호출을 하지 않는다
    running = claude_usage_from_active_run(claude_log_dir) if claude_log_dir is not None else None
    # 두 공급자 조회는 각각 몇 초씩 걸린다 — 동시에 부른다
    with ThreadPoolExecutor(max_workers=2) as pool:
        live = pool.submit(claude_usage_live) if claude_live and running is None else None
        codex = pool.submit(codex_usage) if codex_live else None
        claude = running or (live.result() if live else None)
        openai = codex.result() if codex else _unavailable("openai", "OpenAI · Codex", "Codex 실시간 조회를 끈 상태입니다.")
    if claude is None:
        claude = claude_usage(claude_cache)
        if claude_log_dir is not None:
            claude = _newer(claude, claude_usage_from_logs(claude_log_dir))
    return [claude, openai]
