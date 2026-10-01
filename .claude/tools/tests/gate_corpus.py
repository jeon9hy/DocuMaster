"""게이트 회귀 — 기존 작업 전체에 git 리비전의 gate_check와 지금 작업본의 gate_check를 돌려 출력 차이만 보인다.

    python .claude/tools/tests/gate_corpus.py [--rev HEAD] [--stages 05,06,07]

게이트 규칙을 바꾼 뒤 「의도한 곳만 바뀌었나」를 본다. 문서(작업/)는 읽기만 한다.
리비전 쪽은 그 리비전의 gate_check.py·workspace_files.py·공통/발표_*.md를 임시 폴더에 풀어 돌린다.
비교할 리비전은 gate_check가 DOCUMASTER_WORK_ROOT를 따르는 287c74a 이후여야 한다.
종료 코드: 0 차이 없음 · 1 차이 있음(의도한 변경인지 사람이 본다) · 2 리비전을 못 읽음
"""
from __future__ import annotations

import difflib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[3]
FILES = (".claude/tools/gate_check.py", ".claude/tools/workspace_files.py",
         ".claude/공통/발표_스토리.md", ".claude/공통/발표_브리핑.md", ".claude/공통/발표_학술.md")


def git_show(rev: str, path: str) -> str | None:
    done = subprocess.run(["git", "-c", "core.quotepath=false", "show", f"{rev}:{path}"], cwd=REPO,
                          capture_output=True, encoding="utf-8", errors="replace", check=False)
    return done.stdout if done.returncode == 0 else None


def run_gate(tool: Path, job: str, stage: str) -> str:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "DOCUMASTER_WORK_ROOT": str(REPO)}
    done = subprocess.run([sys.executable, str(tool), job, stage], capture_output=True, encoding="utf-8",
                          errors="replace", env=env, check=False)
    return done.stdout + done.stderr


def main() -> int:
    args = sys.argv[1:]
    rev = args[args.index("--rev") + 1] if "--rev" in args else "HEAD"
    stages = (args[args.index("--stages") + 1] if "--stages" in args else "05,06,07").split(",")
    jobs = sorted(p.name for p in (REPO / "작업").iterdir() if (p / "workspace").is_dir())
    with tempfile.TemporaryDirectory() as tmp:
        for path in FILES:
            text = git_show(rev, path)
            if text is None and path.endswith(".py") and path.endswith("gate_check.py"):
                print(f"[중단] {rev}에 {path}가 없다")
                return 2
            if text is not None:
                target = Path(tmp) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
        old_tool, new_tool = Path(tmp) / FILES[0], REPO / FILES[0]
        changed = 0
        for job in jobs:
            for stage in stages:
                old, new = run_gate(old_tool, job, stage), run_gate(new_tool, job, stage)
                if old == new:
                    continue
                changed += 1
                print(f"\n## {job} · {stage}")
                diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
                print("\n".join(line for line in diff if not line.startswith(("---", "+++", "@@"))))
    print(f"\n게이트 회귀: 작업 {len(jobs)}개 × {'·'.join(stages)} — {rev} 대비 바뀐 출력 {changed}건")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
