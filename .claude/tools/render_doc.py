"""DOC 07 굽기 — 기계 검사 · HTML · PDF · 모아보기를 한 번에 돌리고 판단할 것만 출력한다(doc-finish §1).

    python .claude/tools/render_doc.py <작업ID> [--pages 3,7] [--no-gate]

왜 이게 있는가 — 로이드가 세 도구를 따로 부르고 각 출력을 다시 읽느라 렌더에만 턴 열 번 가까이 썼다(10-01 실측).
  1. gate_check.py <ID> 07 — FAIL·CHECK만 그대로 보이고 OK는 개수만 센다
  2. md2html.py — workspace의 **최신** 07(_v02 …)을 `output/<ID>.html`로. `경고:` 줄만 보인다
  3. make_pdf.py — `output/<ID>.pdf` + `output/contact.png`(+ --pages 확대). 쪽수·검사 결과·장 이동 줄만 보인다
종료 코드: 0 통과 · 1 게이트 FAIL(렌더는 했다 — 아냐에게 보낼 것) · 2 입력 없음 · 3 렌더 실패(PDF를 쓰지 않는다)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-005)
except Exception:
    pass

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from workspace_files import latest, work_root  # noqa: E402

ROOT = work_root()
DOC_BASE = "07_final_document"
# make_pdf 출력에서 판단에 필요한 줄
PDF_KEEP = re.compile(r"^(크기:|본문 글자|장 새 쪽|모아보기:|확대:|검사 결과:|인쇄 실패|Edge)")


def run(*args: str) -> tuple[int, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def gate(job_id: str) -> tuple[int, list[str]]:
    code, out = run(str(TOOLS / "gate_check.py"), job_id, "07")
    lines = out.splitlines()
    ok = sum(1 for line in lines if line.startswith("OK"))
    shown = [line for line in lines if line.startswith(("FAIL", "CHECK", "[중단]", "Traceback"))]
    result = next((line for line in reversed(lines) if line.startswith("결과:")), "결과: (요약 없음)")
    return code, shown + [f"OK {ok}건 생략 · {result}"]


def main() -> int:
    args = sys.argv[1:]
    pages = ""
    if "--pages" in args:
        i = args.index("--pages")
        pages = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    skip_gate = "--no-gate" in args
    args = [a for a in args if a != "--no-gate"]
    if len(args) != 1:
        print(__doc__)
        return 2
    job_id = args[0]
    base = ROOT / "작업" / job_id
    doc = latest(base / "workspace", DOC_BASE)
    if doc is None:
        print(f"[중단] 07이 없다: 작업/{job_id}/workspace/{DOC_BASE}.md")
        return 2
    out_dir = base / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    html, pdf = out_dir / f"{job_id}.html", out_dir / f"{job_id}.pdf"
    print(f"# render_doc · {job_id} · {doc.name}")

    gate_code = 0
    if not skip_gate:
        gate_code, lines = gate(job_id)
        print("\n## 1. 기계 검사 (gate_check 07)")
        print("\n".join(lines))

    print("\n## 2. HTML")
    code, out = run(str(TOOLS / "md2html.py"), str(doc), str(html))
    warnings = [line for line in out.splitlines() if line.startswith("경고")]
    if code != 0 or not html.is_file():
        print(out.strip()[-1500:])
        print("\n렌더: FAIL — HTML을 만들지 못했다")
        return 3
    print("\n".join(dict.fromkeys(warnings)) or "경고 없음")

    print("\n## 3. PDF")
    command = [str(TOOLS / "make_pdf.py"), str(html), str(pdf), "--label", job_id, "--contact"]
    if pages:
        command += ["--pages", pages]
    code, out = run(*command)
    kept = [line for line in out.splitlines() if PDF_KEEP.match(line)]
    print("\n".join(kept) or out.strip()[-1500:])
    if code != 0:
        print("\n렌더: FAIL — 위 검사 결과를 고치기 전에는 이 PDF를 쓰지 않는다")
        return 3

    verdict = "기계 검사 FAIL — 아냐에게 보낸다" if gate_code else "통과 — Lite Review와 contact.png를 본다"
    print(f"\n렌더: OK · {verdict}")
    return 1 if gate_code else 0


if __name__ == "__main__":
    sys.exit(main())
