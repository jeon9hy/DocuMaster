"""`.data/logs/`의 보존 규칙 — 오래된 실행 로그만 지운다. DB·DB 백업·`.data/smoke/`(인수인계 증거)는 건드리지 않는다.

실행 로그 한 벌 = `run_<id>.jsonl` · `run_<id>_models.json` · `run_<id>_telemetry.jsonl`.
한 벌에서 가장 최근에 바뀐 파일을 기준으로 N일이 지났고, 그 실행이 끝났을 때만 한 벌을 통째로 지운다.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

log = logging.getLogger(__name__)

_RUN_FILE = re.compile(r"^(run_[0-9a-f]+)(?:_models\.json|_telemetry\.jsonl|\.jsonl)$")


def prune_run_logs(log_dir: Path, days: int, keep_run_ids: set[str], now: float | None = None) -> list[Path]:
    """지운 파일 목록. days <= 0이면 아무것도 지우지 않는다."""
    if days <= 0 or not log_dir.is_dir():
        return []
    now = time.time() if now is None else now
    groups: dict[str, list[Path]] = {}
    for path in log_dir.iterdir():
        match = _RUN_FILE.match(path.name)
        if match and path.is_file():
            groups.setdefault(match[1], []).append(path)
    removed: list[Path] = []
    for run_id, paths in groups.items():
        if run_id in keep_run_ids:
            continue
        try:
            newest = max(path.stat().st_mtime for path in paths)
        except OSError:
            continue
        if now - newest < days * 86400:
            continue
        for path in paths:
            try:
                path.unlink()
                removed.append(path)
            except OSError as error:
                log.warning("오래된 실행 로그를 지우지 못했습니다(%s): %s", path.name, error)
    if removed:
        log.info("보존 기간(%d일)이 지난 실행 로그 %d개를 지웠습니다.", days, len(removed))
    return removed
