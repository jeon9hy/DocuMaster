"""`상태.md`·`기록.md`를 한 줄 명령으로 갱신한다(양식: `.claude/로이드/상태파일.md`).

왜 이게 있는가 — 로이드가 표를 직접 Edit하면 턴마다 긴 문맥이 다시 실리고(한 실행에 `상태.md` 수정 24번),
칸이 어긋나는 실수도 생긴다. 도구가 양식대로 한 번에 쓴다. 요르 세션 ID는 `_yor_sessions.json`에서 자동으로 옮긴다.

사용:
    python .claude/tools/stage.py init   --id ID --topic "<한 줄 주제>" --mode DOCUMENT|PRESENTATION
    python .claude/tools/stage.py done   <단계> --id ID [--output 경로] [--note 비고] [공통 옵션]
    python .claude/tools/stage.py set    --id ID [공통 옵션]
    python .claude/tools/stage.py log    --id ID "<기록 한 줄>"
    python .claude/tools/stage.py finish --id ID --kind <유형> --manifest "<파일명 · 비고>"   # DOC: output/ID.pdf를 최종/<유형>/ID/로 복사
    python .claude/tools/stage.py finish --id ID --final 최종/발표/ID/파일                     # PPT: promote가 이미 옮긴 파일
공통 옵션:
    --status "진행 중 03 검증질문"   상태 줄        --next "<한 줄>"   다음에 할 일
    --session "유리 에이전트=<id>"   세션 칸(여러 번) --open "<전체>"    열린 것 칸
    --plan "<전체>"                  기획 칸          --log "<한 줄>"    기록.md에 덧붙임(날짜 자동)

`done <단계>`는 진행 표에서 첫 칸이 <단계>이거나 「<단계> 」로 시작하는 행을 완료로 바꾸고, 없으면 행을 더한다.
`finish`는 세션 칸에 자리표시자(`실행 후 기록`·`(미실행)`)가 남아 있거나 최종 파일이 없으면 쓰지 않고 멈춘다(종료 코드 1).
`--kind`는 글 유형에서 가운뎃점을 뺀 이름(현황기록·설명해설·분석·평가비평·제안설득·안내절차·서사소개)이다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 죽지 않게(E-024)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_files import work_root  # noqa: E402

ROOT = work_root()
PLACEHOLDER = re.compile(r"실행 후 기록|\(미실행\)")
DOC_KINDS = ("현황기록", "설명해설", "분석", "평가비평", "제안설득", "안내절차", "서사소개")
YOR_SESSION_FIELDS = {"research": "요르 조사 세션 ID", "plan": "요르 기획 세션 ID"}


class Stop(Exception):
    pass


def paths(work_id: str, root: Path = ROOT) -> tuple[Path, Path, Path]:
    base = root / "작업" / work_id
    return base, base / "상태.md", base / "기록.md"


def template(work_id: str, topic: str, mode: str) -> str:
    doc = mode == "DOCUMENT"
    sessions = " · ".join([
        "요르 조사 세션 ID: (실행 후 기록)",
        "요르 기획 세션 ID: " + ("해당 없음(DOC)" if doc else "(실행 후 기록)"),
        "유리 에이전트: (실행 후 기록)",
        "아냐 에이전트: " + ("(실행 후 기록)" if doc else "해당 없음(PPT)"),
        "실제 모델: 미확인",
    ])
    return "\n".join([
        f"# {work_id} — {topic} · 모드: {mode}",
        "상태: 진행 중 00·01",
        "다음에 할 일: 00·01 작성 → 기획 게이트",
        "",
        "## 요청      상세는 workspace/00",
        "## 기획      개정 번호 r1",
        "## 진행      | 단계 | 산출물 | 상태 | 비고 |",
        "|---|---|---|---|",
        f"## 세션      {sessions}",
        "## 열린 것   검증 라운드 0/1 · 자료 보완 0/1",
        "",
    ])


def set_line(lines: list[str], prefix: str, value: str, limit: int | None = None) -> None:
    """`prefix`로 시작하는 줄의 값을 바꾼다. 상태·다음 할 일은 첫 줄들에만 있다(limit)."""
    scope = lines if limit is None else lines[:limit]
    for index, line in enumerate(scope):
        if line.startswith(prefix):
            head = line[: len(prefix)]
            gap = re.match(r"\s*", line[len(prefix):]).group(0) or " "
            lines[index] = f"{head}{gap}{value}"
            return
    raise Stop(f"`{prefix.strip()}` 줄이 없다 — 상태파일.md 양식인지 확인")


def set_session(lines: list[str], key: str, value: str) -> None:
    index = next((i for i, line in enumerate(lines) if line.startswith("## 세션")), None)
    if index is None:
        raise Stop("`## 세션` 줄이 없다")
    line = lines[index]
    pattern = re.compile(rf"({re.escape(key)}:\s*)([^·]*?)(\s*(?:·|$))")
    if pattern.search(line):
        lines[index] = pattern.sub(lambda m: f"{m.group(1)}{value}{m.group(3)}", line, count=1)
    else:
        lines[index] = line.rstrip() + f" · {key}: {value}"


def table_bounds(lines: list[str]) -> tuple[int, int]:
    """진행 표 행의 [시작, 끝) — `## 진행` 다음 줄부터 다음 `## ` 전까지의 `|` 줄."""
    start = next((i for i, line in enumerate(lines) if line.startswith("## 진행")), None)
    if start is None:
        raise Stop("`## 진행` 줄이 없다")
    end = start + 1
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return start + 1, end


def cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def mark_row(lines: list[str], stage: str, state: str, output: str | None, note: str | None) -> None:
    first, end = table_bounds(lines)
    for index in range(first, end):
        row = cells(lines[index])
        if set(lines[index].replace("|", "").strip()) <= {"-", ":", " "}:
            continue  # 구분선
        if row and (row[0] == stage or row[0].startswith(stage + " ")):
            row += [""] * (4 - len(row))
            row[2] = state
            if output is not None:
                row[1] = output
            if note is not None:
                row[3] = note
            lines[index] = "| " + " | ".join(row[:4]) + " |"
            return
    lines.insert(end, f"| {stage} | {output or '-'} | {state} | {note or ''} |")


def manifest_kind(final: str) -> str:
    """최종/<유형>/<ID>/<파일>의 유형 폴더 이름. 옛 최종/<ID>/<파일>에는 유형이 없다."""
    parts = Path(final).as_posix().split("/")
    return parts[1] if len(parts) >= 4 and parts[0] == "최종" else ""


def copy_yor_sessions(lines: list[str], base: Path) -> None:
    try:
        sessions = json.loads((base / "_yor_sessions.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for kind, field in YOR_SESSION_FIELDS.items():
        if isinstance(sessions.get(kind), str) and sessions[kind]:
            set_session(lines, field, sessions[kind])


def append_log(log_path: Path, work_id: str, text: str, today: str) -> None:
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else f"# 기록 — {work_id}\n"
    if not existing.endswith("\n"):
        existing += "\n"
    log_path.write_text(existing + f"- {today} {text.strip()}\n", encoding="utf-8", newline="\n")


def apply_common(lines: list[str], args: argparse.Namespace) -> None:
    if args.status:
        set_line(lines, "상태:", args.status, limit=5)
    if args.next:
        set_line(lines, "다음에 할 일:", args.next, limit=5)
    if args.plan:
        set_line(lines, "## 기획", args.plan)
    if args.open:
        set_line(lines, "## 열린 것", args.open)
    for pair in args.session or []:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip() or not value.strip():
            raise Stop(f"--session은 `이름=값` 형식이다: {pair}")
        set_session(lines, key.strip(), value.strip())


def run(argv: list[str], root: Path = ROOT, today: str | None = None) -> str:
    parser = argparse.ArgumentParser(prog="stage.py", description="상태.md·기록.md 갱신")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--id", required=True)
        p.add_argument("--status")
        p.add_argument("--next")
        p.add_argument("--plan")
        p.add_argument("--open")
        p.add_argument("--session", action="append")
        p.add_argument("--log")

    init = sub.add_parser("init")
    init.add_argument("--id", required=True)
    init.add_argument("--topic", required=True)
    init.add_argument("--mode", required=True, choices=["DOCUMENT", "PRESENTATION"])
    done = sub.add_parser("done")
    done.add_argument("stage")
    done.add_argument("--output")
    done.add_argument("--note")
    common(done)
    common(sub.add_parser("set"))
    log = sub.add_parser("log")
    log.add_argument("--id", required=True)
    log.add_argument("text")
    finish = sub.add_parser("finish")
    finish.add_argument("--id", required=True)
    where = finish.add_mutually_exclusive_group(required=True)
    where.add_argument("--kind", choices=DOC_KINDS, help="DOC: output/<ID>.pdf를 최종/<유형>/<ID>/로 복사")
    where.add_argument("--final", help="이미 이관된 최종 파일(PPT promote)")
    finish.add_argument("--manifest")
    args = parser.parse_args(argv)
    today = today or date.today().isoformat()

    base, state_path, log_path = paths(args.id, root)
    if args.command == "init":
        if state_path.exists():
            raise Stop(f"이미 있다: {state_path.relative_to(root)} — 덮어쓰지 않는다")
        base.mkdir(parents=True, exist_ok=True)
        state_path.write_text(template(args.id, args.topic, args.mode), encoding="utf-8", newline="\n")
        if not log_path.exists():
            log_path.write_text(f"# 기록 — {args.id}\n", encoding="utf-8", newline="\n")
        return f"stage init: {args.id} · {args.mode}"
    if args.command == "log":
        if not base.is_dir():  # 오타 난 ID로 빈 작업 폴더를 만들지 않는다
            raise Stop(f"작업/{args.id} 가 없다 — 작업 ID를 확인한다")
        append_log(log_path, args.id, args.text, today)
        return f"stage log: {args.id}"
    if not state_path.exists():
        raise Stop(f"{state_path.relative_to(root)} 가 없다 — 먼저 `stage.py init`")

    lines = state_path.read_text(encoding="utf-8").splitlines()
    copy_yor_sessions(lines, base)
    if args.command == "finish":
        session_line = next((line for line in lines if line.startswith("## 세션")), "")
        if PLACEHOLDER.search(session_line):
            raise Stop("세션 칸의 자리표시자를 실제 ID 또는 `해당 없음(이유)`으로 닫아야 한다 — "
                       "`stage.py set --session \"이름=값\"`")
        if args.kind:  # 최종 경로를 손으로 쓰지 않는다 — 유형 폴더 계약(CLAUDE.md §4)대로 도구가 옮긴다
            rendered = base / "output" / f"{args.id}.pdf"
            if not rendered.is_file():
                raise Stop(f"렌더된 PDF가 없다: 작업/{args.id}/output/{args.id}.pdf — render_doc을 먼저 한다")
            args.final = f"최종/{args.kind}/{args.id}/{args.id}.pdf"
            (root / args.final).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rendered, root / args.final)
        if not (root / args.final).is_file():
            raise Stop(f"--final 파일이 없다: {args.final} — 이관(promote)을 먼저 한다")
        set_line(lines, "상태:", "완료", limit=5)
        set_line(lines, "다음에 할 일:", f"없음 — {args.final}", limit=5)
        state_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        if args.manifest:
            manifest = root / "최종" / "_manifest.md"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            text = manifest.read_text(encoding="utf-8") if manifest.exists() else ""
            if f"`{args.id}`" not in text:
                if text and not text.endswith("\n"):
                    text += "\n"
                kind = manifest_kind(args.final)
                label = f"[{kind}] " if kind else ""
                manifest.write_text(text + f"- {today} · {label}`{args.id}` · {args.manifest}\n", encoding="utf-8",
                                    newline="\n")
        return f"stage finish: {args.id} · 완료"

    if args.command == "done":
        mark_row(lines, args.stage, "완료", args.output, args.note)
    apply_common(lines, args)
    state_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if args.log:
        append_log(log_path, args.id, args.log, today)
    return f"stage {args.command}: {args.id}" + (f" · {args.stage} 완료" if args.command == "done" else "")


def main() -> int:
    try:
        print(run(sys.argv[1:]))
    except Stop as error:
        print(f"stage: FAIL — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
