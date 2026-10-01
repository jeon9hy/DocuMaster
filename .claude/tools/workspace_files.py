"""도구들이 함께 쓰는 경로·버전 규칙 — 번호는 계약이고 수정본은 `_v02`처럼 쌓는다(CLAUDE.md §4).

    RULES       .claude/
    work_root() 작업/·최종/이 있는 곳. 테스트만 DOCUMASTER_WORK_ROOT로 임시 폴더를 준다(부를 때마다 다시 읽는다)
    latest(ws, "05_verified_research_pack")  → 가장 높은 버전 파일(없으면 None)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

RULES = Path(__file__).resolve().parents[1]
HEADER_END = "--- 헤더 끝 ---"


def work_root() -> Path:
    return Path(os.environ.get("DOCUMASTER_WORK_ROOT") or RULES.parent).resolve()


def versioned(ws: Path, base: str) -> list[tuple[int, Path]]:
    """workspace의 `<base>.md`·`<base>_vNN.md`를 (버전, 경로)로, 버전순. `_v1`이 없는 원본은 1이다."""
    found = []
    for path in ws.glob(base + "*.md"):
        m = re.fullmatch(re.escape(base) + r"(?:_v(\d+))?\.md", path.name)
        if m:
            found.append((int(m[1] or 1), path))
    return sorted(found)


def latest(ws: Path, base: str) -> Path | None:
    found = versioned(ws, base)
    return found[-1][1] if found else None


def next_version(ws: Path, base: str) -> Path:
    found = versioned(ws, base)
    return ws / f"{base}_v{(found[-1][0] if found else 1) + 1:02d}.md"
