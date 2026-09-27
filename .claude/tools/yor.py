"""요르(Codex) 호출 — 로이드가 codex 명령을 손으로 조립하지 않게 한다.

    python .claude/tools/yor.py research --id <ID> [--image <png> ...]   # 02  조사 세션 새로
    python .claude/tools/yor.py answer   --id <ID> [--retry]              # 04  조사 세션 resume → 02 다음 버전
    python .claude/tools/yor.py plan     --id <ID>                        # PPT 06  기획 세션 새로(덱 유형은 00에서)
    python .claude/tools/yor.py pack     --id <ID>                        # PPT 07  기획 세션 resume
    python .claude/tools/yor.py patch    --id <ID> --target <workspace 파일명>   # _입력_patch.md → 다음 버전
    python .claude/tools/yor.py wait     --id <ID>                        # 백그라운드로 넘어간 호출을 기다린다

지키는 것
  * 모델·추론 강도는 DOCUMASTER_AGENT_MODELS(웹앱 실행 스냅샷)에서 호출마다 다시 읽는다. 환경변수가 있는데 못 읽으면
    호출하지 않는다. 없을 때만 기본값(gpt-5.6-sol · xhigh). 로그 머리의 실제 모델·강도가 다르면 실패다.
  * 입력(00·01·03·05)은 경로가 아니라 stdin에 붙인다 — Codex는 한글 경로의 파일을 셸로 못 읽는다(E-051).
  * 세션 ID는 `_yor_sessions.json`에 남기고 resume은 그 ID로만 한다(`--last` 금지, E-007).
  * 한 작업에 요르 호출은 하나씩이다. 진행 중이면 새로 시작하지 않고 `wait`을 안내한다.
  * 종료 코드·출력 파일·헤더·실제 모델을 함께 본다(E-030). 마지막 줄이 `요르 <종류>: OK|FAIL …`.
종료 코드: 0 OK · 1 호출·산출 실패 · 2 입력·설정 오류 · 3 모델 불일치 · 75 아직 진행 중(wait을 다시)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-005·E-024)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_patch  # noqa: E402

RULES = Path(__file__).resolve().parents[1]  # .claude/
# 작업/이 있는 곳. 테스트만 DOCUMASTER_WORK_ROOT로 임시 폴더를 준다
ROOT = Path(os.environ.get("DOCUMASTER_WORK_ROOT") or RULES.parent).resolve()
DEFAULT_MODEL = {"model": "gpt-5.6-sol", "effort": "xhigh"}
HEADER_END = "--- 헤더 끝 ---"
WAIT_SECONDS = 540       # Bash 도구 한도(10분) 안에서 돌아온다
CALL_TIMEOUT = 90 * 60   # Codex가 멈춰도 로이드가 끝없이 기다리지 않게
RUNNING, STILL_RUNNING = "running", 75

# 종류 → 절차서 · 세션 · 붙일 입력 · 출력 · 로그. 입력 이름은 workspace의 계약 번호(최신 버전을 고른다)
CALLS = {
    "research": {"label": "조사 02", "rules": ["요르/역할.md", "공통/근거정책.md", "요르/조사.md"],
                 "session": ("research", "new"), "inline": ["00_user_brief", "01_research_blueprint"],
                 "web": True, "out": "workspace/02_research_pack.md", "log": "_log_02.txt",
                 "note": "_입력_조사.md", "header": True},
    "answer": {"label": "검증 응답 04", "rules": ["요르/검증응답.md"], "session": ("research", "resume"),
               "inline": ["03_verification_questions"], "web": True, "out": "_raw_04.md", "log": "_log_04.txt",
               "note": "_입력_응답.md", "header": False},
    "plan": {"label": "PPT 세부 기획 06", "rules": ["요르/역할.md", "요르/세부기획.md", "공통/발표규격.md"],
             "session": ("plan", "new"), "inline": ["00_user_brief", "05_verified_research_pack"], "web": False,
             "out": "workspace/06_detailed_plan.md", "log": "_log_06.txt", "note": "_입력_세부기획.md",
             "note_required": True, "header": True},
    "pack": {"label": "PPT 발표팩 07", "rules": ["요르/비주얼_발표.md"], "session": ("plan", "resume"),
             "inline": [], "web": False, "out": "workspace/07_notebooklm_presentation_pack.md",
             "log": "_log_07pack.txt", "note": "_입력_비주얼기획.md", "header": True},
    "patch": {"label": "PATCH", "rules": [], "session": (None, "resume"), "inline": [], "web": False,
              "out": "_raw_patch.md", "log": "_log_patch.txt", "note": "_입력_patch.md", "note_required": True,
              "header": False},
}
PATCH_FORMAT = """고칠 부분만 아래 형식으로 낸다(전문 재출력 금지). OLD는 원본에 정확히 한 번 나오는 문자열이다.
=== 수정 패치 시작 ===
--- PATCH 1 ---
대상: <절·장>
OLD:
<원본 그대로>
NEW:
<바꿀 내용>
--- PATCH 끝 ---
=== 수정 패치 끝 ==="""


class Stop(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def versioned(ws: Path, base: str) -> list[tuple[int, Path]]:
    """workspace의 `<base>.md`·`<base>_vNN.md`를 (버전, 경로)로, 버전순."""
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


def models() -> dict:
    """호출 직전에 실행 스냅샷을 다시 읽는다(이전 호출의 값을 재사용하지 않는다)."""
    path = os.environ.get("DOCUMASTER_AGENT_MODELS")
    if not path:
        return dict(DEFAULT_MODEL)
    try:
        yor = json.loads(Path(path).read_text(encoding="utf-8"))["yor"]
        if not yor.get("model") or not yor.get("effort"):
            raise KeyError("model/effort")
        return {"model": str(yor["model"]), "effort": str(yor["effort"])}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Stop(2, f"DOCUMASTER_AGENT_MODELS({path})를 읽지 못했다 — 기본값으로 대신하지 않는다: {error}") from error


def codex_command() -> list[str]:
    override = os.environ.get("DOCUMASTER_CODEX")  # 테스트용: JSON 목록 또는 실행 파일 경로
    if override:
        return json.loads(override) if override.lstrip().startswith("[") else [override]
    found = shutil.which("codex")
    if not found:
        raise Stop(2, "codex를 찾지 못했다 — `npm i -g @openai/codex` 설치와 PATH를 확인한다")
    script = Path(found).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    node = shutil.which("node")
    # Windows의 codex.cmd를 거치지 않는다 — cmd.exe가 인자를 다시 해석하지 않게(E-009)
    return [node, str(script)] if found.lower().endswith(".cmd") and script.is_file() and node else [found]


def alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION — 읽기만
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # POSIX: 신호 0은 존재 확인만
    except OSError:
        return False
    return True


def kill_tree(process: subprocess.Popen) -> None:
    """node → codex.exe까지 함께 끝낸다(node만 죽이면 codex가 남는다)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        process.kill()
    process.wait()


class Job:
    def __init__(self, job_id: str):
        self.id = job_id
        self.base = ROOT / "작업" / job_id
        self.ws = self.base / "workspace"
        self.state_file = self.base / "_yor_call.json"
        self.sessions_file = self.base / "_yor_sessions.json"
        if not self.ws.is_dir():
            raise Stop(2, f"작업 폴더가 없다: 작업/{job_id}/workspace")

    def read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def write_json(self, path: Path, data: dict) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)

    def rel(self, path: Path) -> str:
        return path.relative_to(self.base).as_posix()


def build_prompt(job: Job, kind: str, spec: dict, opts: argparse.Namespace) -> str:
    parts = [(RULES / name).read_text(encoding="utf-8") for name in spec["rules"]]
    if kind == "plan":
        brief = latest(job.ws, "00_user_brief")
        deck = re.search(r"덱 유형[^:\n]*:\s*(스토리|브리핑|학술)", brief.read_text(encoding="utf-8")) if brief else None
        if not deck:
            raise Stop(2, "00에 `덱 유형: 스토리|브리핑|학술`이 없다 — 00을 고친 뒤 부른다(유형을 추정하지 않는다)")
        parts.append((RULES / "공통" / f"발표_{deck[1]}.md").read_text(encoding="utf-8"))
    if opts.retry:
        parts = []  # 같은 세션에 절차서·입력이 이미 있다 — 지시만 보낸다
    header = [f"# 이번 호출: {spec['label']} · 작업 ID {job.id}",
              "입력 파일은 아래에 전문이 붙어 있다. 셸이나 도구로 파일을 다시 읽지 않는다(한글 경로를 못 읽는다, E-051).",
              f"결과는 마지막 응답 본문으로만 낸다 — 파일 쓰기를 시도하지 않는다(로이드가 `{spec['out']}`에 저장한다)."]
    if kind == "patch":
        header.append(PATCH_FORMAT)
    parts.append("\n".join(header))
    note = job.base / spec["note"]
    if note.is_file():
        parts.append(f"## 로이드의 지시 ({spec['note']})\n" + note.read_text(encoding="utf-8"))
    elif spec.get("note_required"):
        raise Stop(2, f"작업/{job.id}/{spec['note']}가 없다 — 지시(채택 결정·고칠 항목)를 먼저 쓴다")
    for base in [] if opts.retry else spec["inline"]:
        path = latest(job.ws, base)
        if not path:
            raise Stop(2, f"입력이 없다: workspace/{base}.md")
        parts.append(f"===== 입력 파일: workspace/{path.name} =====\n{path.read_text(encoding='utf-8')}\n"
                     f"===== 입력 파일 끝: {path.name} =====")
    return "\n\n".join(parts) + "\n"


def rotate(path: Path) -> None:
    """이전 로그·raw를 지우지 않고 _1, _2 …로 남긴다(실패 이력은 기록.md가 가리킨다)."""
    if not path.exists():
        return
    n = 1
    while (old := path.with_name(f"{path.stem}_{n}{path.suffix}")).exists():
        n += 1
    path.replace(old)


def log_header(log: str) -> dict:
    get = lambda key: (re.search(rf"^{key}:\s*(\S+)", log, re.M) or [None, None])[1]  # noqa: E731
    return {"model": get("model"), "effort": get("reasoning effort"), "session": get("session id"),
            "sandbox": get("sandbox")}


def start(opts: argparse.Namespace) -> int:
    job, kind = Job(opts.id), opts.kind
    spec = CALLS[kind]
    if opts.retry and kind not in ("answer", "patch"):
        raise Stop(2, "--retry는 answer·patch의 형식 재요청에만 쓴다")
    state = job.read_json(job.state_file)
    if state.get("status") == RUNNING and alive(int(state.get("pid") or 0)):
        raise Stop(2, f"요르 {state.get('kind')} 호출이 아직 진행 중이다 — 새로 시작하지 말고 "
                      f"`python .claude/tools/yor.py wait --id {job.id}`")
    want = models()
    session_key, how = spec["session"]
    if kind == "patch":
        target = opts.target or ""
        session_key = "plan" if re.match(r"0[67]_", target) else "research"
        if not re.fullmatch(r"0[0-7]_[A-Za-z0-9_]+\.md", target) or not (job.ws / target).is_file():
            raise Stop(2, f"--target은 workspace의 계약 파일명이어야 한다: {target!r}")
    sessions = job.read_json(job.sessions_file)
    session_id = sessions.get(session_key) if how == "resume" else None
    if how == "resume" and not session_id:
        raise Stop(2, f"{session_key} 세션 ID가 `_yor_sessions.json`에 없다 — 새 세션으로 우회하지 않는다")

    prompt = build_prompt(job, kind, spec, opts)
    stdin_path = job.base / f"_stdin_{kind}.md"
    stdin_path.write_text(prompt, encoding="utf-8")
    out, log = job.base / spec["out"], job.base / spec["log"]
    for path in (log, out) if not spec["header"] else (log,):
        rotate(path)  # raw(_raw_04 등)는 재시도 때 덮어쓰지 않는다. 산출물(02·06·07)은 codex가 덮어쓴다
    command = codex_command() + ["exec"] + (["resume", session_id] if session_id else [])
    command += ["-m", want["model"], "-c", f"model_reasoning_effort={want['effort']}", "--skip-git-repo-check"]
    # resume에는 -C·-s가 없고 샌드박스를 잇지 않는다(실측 workspace-write, E-007) — 설정 덮어쓰기로 읽기 전용을 건다
    command += ["-C", str(ROOT), "-s", "read-only"] if not session_id else ["-c", 'sandbox_mode="read-only"']
    if spec["web"]:
        command += ["-c", "tools.web_search=true"]
    for image in opts.image or []:
        command += ["-i", str(Path(image).resolve())]
    command += ["-o", str(out), "-"]

    started = time.time()
    with stdin_path.open("rb") as stdin, log.open("wb") as log_file:
        process = subprocess.Popen(command, cwd=ROOT, stdin=stdin, stdout=log_file, stderr=subprocess.STDOUT)
        job.write_json(job.state_file, {"status": RUNNING, "kind": kind, "pid": os.getpid(), "codex_pid": process.pid,
                                        "started_at": now(), "log": job.rel(log), "out": job.rel(out)})
        print(f"요르 {spec['label']} 시작 · {want['model']}/{want['effort']} · 로그 {job.rel(log)} — 끝날 때까지 기다린다", flush=True)
        try:
            code = process.wait(timeout=CALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            kill_tree(process)
            code = None
    summary, exit_code = finish(job, kind, spec, opts, code, want, session_key if how == "new" else None,
                                out, log, time.time() - started)
    job.write_json(job.state_file, {"status": "done", "kind": kind, "exit": exit_code, "summary": summary,
                                    "finished_at": now()})
    print(summary)
    return exit_code


def finish(job: Job, kind: str, spec: dict, opts, code: int | None, want: dict, new_session: str | None,
           out: Path, log: Path, seconds: float) -> tuple[str, int]:
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    got = log_header(text)
    notes, exit_code = [], 0
    if code is None:
        notes.append(f"{CALL_TIMEOUT // 60}분 안에 끝나지 않아 중단")
        exit_code = 1
    elif code != 0:
        tail = next((line for line in reversed(text.splitlines()) if line.strip()), "")
        notes.append(f"종료 코드 {code} — {tail[:160]}")
        exit_code = 1
    body = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
    if not body.strip():
        notes.append(f"출력이 비었다({job.rel(out)})")
        exit_code = exit_code or 1
    elif spec["header"] and HEADER_END not in body:
        notes.append(f"`{HEADER_END}`이 없다 — 형식 확인")
    mismatch = [f"{name} {got[name]}≠{want[name]}" for name in ("model", "effort") if got[name] and got[name] != want[name]]
    if mismatch:
        notes.append("실제 호출값이 설정과 다르다: " + ", ".join(mismatch))
        exit_code = 3
    if got["sandbox"] and got["sandbox"] != "read-only":
        notes.append(f"샌드박스가 read-only가 아니었다({got['sandbox']}) — 산출물 외 파일 변경이 없는지 `git status`로 본다")
    if new_session and got["session"]:
        sessions = job.read_json(job.sessions_file)
        sessions[new_session] = got["session"]
        job.write_json(job.sessions_file, sessions)
    if exit_code == 0 and kind in ("answer", "patch"):
        exit_code = apply(job, kind, opts, out, notes)
    actual = f"{got['model'] or '미확인'}/{got['effort'] or '미확인'}"
    session = got["session"] or "미확인"
    line = (f"요르 {kind}: {'OK' if exit_code == 0 else 'FAIL'} · {job.rel(out)} {len(body.encode('utf-8')):,}B · "
            f"요청 {want['model']}/{want['effort']} · 실제 {actual} · 세션 {session} · {seconds / 60:.1f}분 · 로그 {job.rel(log)}")
    if new_session and got["session"]:
        line += f"\n상태.md `## 세션`에 적는다: 요르 {'조사' if new_session == 'research' else '기획'} 세션 {got['session']}"
    return line + "".join(f"\n  - {note}" for note in notes), exit_code


def apply(job: Job, kind: str, opts, raw: Path, notes: list[str]) -> int:
    """04 응답·PATCH를 적용기로 넘긴다. 실패하면 아무것도 쓰지 않고 요르에게 돌려줄 문장을 남긴다."""
    base = "02_research_pack" if kind == "answer" else re.sub(r"(_v\d+)?\.md$", "", opts.target)
    src = latest(job.ws, base)
    if not src:
        notes.append(f"적용할 원본이 없다: workspace/{base}.md")
        return 2
    dest = next_version(job.ws, base)
    answers = job.ws / "04_verification_answers.md" if kind == "answer" else None
    print(f"--- 적용기: {src.name} → {dest.name}")
    code = apply_patch.run(str(src), str(dest), str(raw), str(answers) if answers else None)
    if code:
        notes.append(f"적용 실패 — 위 메시지를 `{CALLS[kind]['note']}`에 옮겨 `--retry`로 한 번만 돌려준다")
    return code


def wait(opts: argparse.Namespace) -> int:
    job = Job(opts.id)
    deadline = time.time() + opts.seconds
    while True:
        state = job.read_json(job.state_file)
        if not state:
            raise Stop(2, "진행 중이거나 끝난 요르 호출 기록이 없다")
        if state.get("status") != RUNNING:
            print(state.get("summary") or f"요르 {state.get('kind')}: 끝남(요약 없음)")
            return int(state.get("exit", 1))
        if not alive(int(state.get("pid") or 0)):
            state.update(status="done", exit=1, summary=f"요르 {state.get('kind')}: FAIL · 호출 프로세스가 결과를 남기지 않고 끝났다"
                                                        f" — 로그 {state.get('log')}를 보고 다시 부른다")
            job.write_json(job.state_file, state)
            continue
        if time.time() >= deadline:
            print(f"요르 {state.get('kind')}: RUNNING · {state.get('started_at')} 시작 — 턴을 끝내지 말고 같은 명령을 다시 부른다")
            return STILL_RUNNING
        time.sleep(5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=[*CALLS, "wait"])
    parser.add_argument("--id", required=True, help="작업 ID")
    parser.add_argument("--image", action="append", help="research: 참고자료 스캔본 PNG(4~6장)")
    parser.add_argument("--retry", action="store_true", help="answer·patch 재요청: 지시 파일만 보낸다")
    parser.add_argument("--target", help="patch: 고칠 workspace 파일명(예: 06_detailed_plan.md)")
    parser.add_argument("--seconds", type=int, default=WAIT_SECONDS, help="wait: 최대 대기 초")
    opts = parser.parse_args()
    try:
        return wait(opts) if opts.kind == "wait" else start(opts)
    except Stop as stop:
        print(f"요르 {opts.kind}: FAIL · {stop}")
        return stop.code


if __name__ == "__main__":
    sys.exit(main())
