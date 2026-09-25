"""가짜 로이드 세션 — LLM을 부르지 않는다. 백엔드·SSE·파일 감시·재개 경로를 비용 없이 검증하는 용도.

`claude -p --output-format stream-json`과 같은 모양(init · result 줄)을 stdout에 내고,
작업 폴더에는 실제 계약 파일명(00~07 · 상태.md · output/ · 최종/)으로 짧은 더미 내용을 쓴다.
실제 작업/·최종/이 아니라 백엔드가 넘겨준 샌드박스(--work-root)에만 쓴다.

턴 구성(실제 로이드가 사용자에게 묻고 턴을 끝내는 것을 흉내 낸다):
  1턴: 00 · 01 작성 → 기획 확인을 묻고 끝
  2턴(--resume): 02 → 03 → 04 → 05 → 문서 07 / 발표 06→07 → output → 최종 → 완료 보고
요청에 넣는 표시(테스트용):
  [blocked]      05를 「검증 보류」로 쓰고 한 번 더 묻는다
  [fail]         00 뒤 오류로 끝난다
  [ambiguous]    작업 폴더를 만들기 전에 모드를 묻고 끝낸다(실제 로이드의 모드 판정 질문)
  [autocontinue] 1턴을 사용자 대기가 아닌 「진행 중」 상태로 끝낸다 — 백엔드가 알아서 이어 가야 한다
  [stall]        이어 받은 턴에서 아무 파일도 쓰지 않고 끝낸다(무한 반복 방지 확인)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

PRESENTATION_WORDS = ("발표", "ppt", "슬라이드", "presentation", "덱")


def emit(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def tiny_pdf(title: str) -> bytes:
    """글자 한 줄짜리 1쪽 PDF(미리보기 확인용)."""
    text = title.encode("ascii", "replace").decode()
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


class FakeLoid:
    def __init__(self, work_root: Path, session_id: str, step: float):
        self.id = f"fake_{date.today():%Y%m%d}_{session_id[:6]}"
        self.base = work_root / "작업" / self.id
        self.final = work_root / "최종" / self.id
        self.workspace = self.base / "workspace"
        self.step = step
        self.session_id = session_id

    # --- 파일 ------------------------------------------------------------------
    def write(self, name: str, text: str) -> None:
        time.sleep(self.step)
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / name).write_text(text.strip() + "\n", encoding="utf-8")

    def state(self, status: str, mode: str) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "상태.md").write_text(
            f"# {self.id} — 가짜 실행 · 모드: {mode}\n상태: {status}\n다음에 할 일: (가짜 오케스트레이터)\n",
            encoding="utf-8",
        )

    def request_text(self) -> str:
        path = self.base / "_요청.txt"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    # --- 턴 --------------------------------------------------------------------
    def first_turn(self, prompt: str) -> str:
        if "[ambiguous]" in prompt:
            return "문서와 발표 중 어느 형식으로 만들까요?"  # 폴더도 만들지 않는다
        mode = "PRESENTATION" if any(word in prompt.lower() for word in PRESENTATION_WORDS) else "DOCUMENT"
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "_요청.txt").write_text(prompt, encoding="utf-8")
        self.state("진행 중 00·01", mode)
        self.write("00_user_brief.md", f"""
# User Brief
- 작업 ID: {self.id} / 모드: {mode} / 작성일: {date.today()}
- 원문 요청: {prompt.splitlines()[0] if prompt else ""}
--- 헤더 끝 ---
## 목적
가짜 오케스트레이터가 쓴 요청 정리입니다.
""")
        if "[fail]" in prompt:
            sys.stderr.write("fake orchestrator: 요청에 [fail]이 있어 오류로 끝냅니다.\n")
            sys.exit(2)
        self.write("01_research_blueprint.md", """
# Research Blueprint
## 핵심 질문
1. 현황은 어떤가?
2. 무엇이 원인인가?
""")
        if "[autocontinue]" in prompt:
            self.state("진행 중 02", mode)
            return "00·01을 작성했고 기획 게이트를 통과했습니다. 자료조사로 넘어갑니다."
        self.state("사용자 승인 대기 — 기획 확인", mode)
        return "00·01을 작성했고 기획 게이트를 통과했습니다. 이 기획대로 자료조사를 시작할까요?"

    def continue_turn(self, answer: str) -> str:
        if not (self.workspace / "00_user_brief.md").exists():  # 폴더 전에 물었던 경우 — 답으로 시작
            return self.first_turn(answer)
        if "[stall]" in self.request_text():
            return "확인하고 있습니다."
        brief = (self.workspace / "00_user_brief.md").read_text(encoding="utf-8")
        mode = "PRESENTATION" if "모드: PRESENTATION" in brief else "DOCUMENT"
        blocked_requested = "[blocked]" in self.request_text()
        if not (self.workspace / "01_research_blueprint.md").exists():  # 00만 쓰고 멈췄던 경우
            self.write("01_research_blueprint.md", "# Research Blueprint\n## 핵심 질문\n1. 현황은 어떤가?")
            self.state("사용자 승인 대기 — 기획 확인", mode)
            return "01 기획을 마쳤습니다. 이 기획대로 자료조사를 시작할까요?"
        self.state("진행 중 조사·검증", mode)
        if not (self.workspace / "02_research_pack.md").exists():
            self.write("02_research_pack.md", "# Research Pack\n- 주장 A — 출처 1\n- 주장 B — 출처 2 [미확인]")
            self.write("03_verification_questions.md", "# 검증 질문\n1. 주장 A의 기준 시점은?")
            self.write("04_verification_answers.md", "# 검증 응답\n1. 2025년 기준")
            if blocked_requested:
                self.write("05_verified_research_pack.md", "검증 보류 — 확인 불가\n# Verified Research Pack\n- 판정: blocked")
                self.state("사용자 승인 대기 — 검증 보류", mode)
                return "검증 보류 — 확인 불가. 핵심 주장 A의 원문을 열 수 없습니다. 해당 주장을 제거하고 계속할까요, 자료를 추가하시겠어요?"
            self.write("05_verified_research_pack.md", "검증 통과 — 조건부\n# Verified Research Pack\n- 판정: conditional\n- CAUTION: 주장 A")
        elif blocked_requested and not (self.workspace / "05_verified_research_pack_v02.md").exists():
            self.write("05_verified_research_pack_v02.md", "검증 통과 — 조건부\n# Verified Research Pack\n- 판정: conditional (주장 A REMOVE)")

        self.state("진행 중 07" if mode == "DOCUMENT" else "진행 중 06·07", mode)
        if mode == "DOCUMENT":
            self.write("07_final_document.md", "# 최종 문서\n## 요약\n검증을 통과한 근거만으로 쓴 요약입니다.")
            output_name = f"{self.id}.pdf"
        else:
            self.write("06_detailed_plan.md", "# Detailed Plan (LOCKED)\n## 1장 현황\n## 2장 원인")
            self.write("07_notebooklm_presentation_pack.md", "# 발표팩\n## Slide 1 표지\n## Slide 2 결론")
            output_name = f"{self.id}_slides.pdf"

        time.sleep(self.step)
        (self.base / "output").mkdir(parents=True, exist_ok=True)
        (self.base / "output" / output_name).write_bytes(tiny_pdf(self.id))
        time.sleep(self.step)
        self.final.mkdir(parents=True, exist_ok=True)
        (self.final / output_name).write_bytes(tiny_pdf(f"{self.id} final"))
        self.state("완료", mode)
        return f"완료 보고 — 산출물: 최종/{self.id}/{output_name} · 판정: conditional · CAUTION 1건(주장 A) · 가짜 실행이라 실제 모델은 쓰지 않았습니다."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--step-seconds", type=float, default=1.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    prompt = sys.stdin.buffer.read().decode("utf-8")
    loid = FakeLoid(args.work_root, args.session_id, args.step_seconds)
    emit({"type": "system", "subtype": "init", "session_id": args.session_id, "model": "fake-orchestrator"})
    text = loid.continue_turn(prompt) if args.resume else loid.first_turn(prompt)
    emit({"type": "result", "subtype": "success", "is_error": False, "result": text, "session_id": args.session_id})
    return 0


if __name__ == "__main__":
    sys.exit(main())
