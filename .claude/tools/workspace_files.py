"""도구들이 함께 쓰는 경로·버전 규칙 — 번호는 계약이고 수정본은 `_v02`처럼 쌓는다(CLAUDE.md §4).

    RULES       .claude/
    work_root() 작업/·최종/이 있는 곳. 테스트만 DOCUMASTER_WORK_ROOT로 임시 폴더를 준다(부를 때마다 다시 읽는다)
    latest(ws, "05_verified_research_pack")  → 가장 높은 버전 파일(없으면 None)

집필용 05(아냐·doc-revise가 읽는 범위 — 최신 버전의 첫 줄 · §2 · §5)를 출력한다:
    python .claude/tools/workspace_files.py view05 <ID>
"""
from __future__ import annotations

import os
import re
import sys
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


WRITER_SECTIONS = ("2", "5")  # 05 §2 검증된 사실 · §5 출처 — 집필은 이것만 본다(05 §1·§3·§4 금지)


def writer_view(text: str) -> str:
    """05의 첫 줄(판정)과 §2·§5만. 절은 `## <번호>.` 머리에서 다음 번호 절 머리 전까지다."""
    lines = text.splitlines()
    first = next((line for line in lines if line.strip()), "")
    kept, keep = [first], False
    for line in lines:
        head = re.match(r"## (\d+)\.", line)
        if head:
            keep = head[1] in WRITER_SECTIONS
        if keep:
            kept.append(line)
    return "\n".join(kept) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "view05":
        print("사용: python .claude/tools/workspace_files.py view05 <ID>", file=sys.stderr)
        return 2
    ws = work_root() / "작업" / argv[1] / "workspace"
    path = latest(ws, "05_verified_research_pack")
    if path is None:
        print(f"05가 없다: 작업/{argv[1]}/workspace/05_verified_research_pack.md", file=sys.stderr)
        return 1
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-024)
    except Exception:
        pass
    print(f"===== {path.name} (첫 줄 · §2 · §5) =====")
    print(writer_view(path.read_text(encoding="utf-8")), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
