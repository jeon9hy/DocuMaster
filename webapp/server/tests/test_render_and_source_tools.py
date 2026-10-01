"""렌더 묶음(render_doc.py)·원문 대조(source_check.py) — 모델·네트워크·Edge 없이 확인한다."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[3] / ".claude" / "tools"
ID = "도구_20261002"


def load(name: str, monkeypatch, root: Path):
    monkeypatch.setenv("DOCUMASTER_WORK_ROOT", str(root))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIED = """검증 통과 — 조건부
# Verified Research Pack
- APPROVED 2 · CORRECTED 0 · REMOVE 0 · CAUTION 0
--- 헤더 끝 ---
## 2. 검증된 사실
- 조기 퇴사 16.5% (S01)
## 5. 출처
- S01 | 조기퇴사 조사 | 잡코리아 | 2021-08-02 | https://example.com/a
- S02 | 청년층 부가조사 | 통계청 | 2025-07-24 | https://example.com/b.pdf
- S03 | 보고서 | PwC | 2025 | https://www.pwc.com/report.pdf
- S04 | 내부 자료 | 기관 | 2026 | 자료/메모.txt
"""


@pytest.fixture
def job(tmp_path):
    ws = tmp_path / "작업" / ID / "workspace"
    ws.mkdir(parents=True)
    (ws / "05_verified_research_pack.md").write_text(VERIFIED, encoding="utf-8")
    return tmp_path, ws


# --- source_check -------------------------------------------------------------


def test_number_pattern_ignores_spacing_commas_and_longer_numbers(monkeypatch, tmp_path):
    sc = load("source_check", monkeypatch, tmp_path)
    assert sc.pattern_of("16.5").search("평균 1 6 . 5 %")
    assert sc.pattern_of("3508").search("2025. 5 3,607 3,508 1,608")
    assert sc.pattern_of("3,508").search("합계 3508명")
    assert not sc.pattern_of("16.5").search("116.5 · 16.52 · 16.5.1")
    assert sc.pattern_of("신입사원 조기 퇴사").search("신입사원  조기\n퇴사")
    # 한국어 단위 — 원문이 풀어 쓴 금액도 같은 값으로 본다
    assert sc.pattern_of("659만").search("상한액: 6,590,000원")
    assert sc.pattern_of("270만").search("월평균 보수 270만 원 미만")
    assert not sc.pattern_of("659만").search("6,590,001원")


def test_targets_split_numbers_but_keep_quotes_and_thousands(monkeypatch, tmp_path):
    sc = load("source_check", monkeypatch, tmp_path)
    assert sc.parse_targets(["S01=16.5,64.9%", "S03=3,508", "S07=직무 적합성, 불일치|사내 문화"]) == {
        "S01": ["16.5", "64.9%"], "S03": ["3,508"], "S07": ["직무 적합성, 불일치", "사내 문화"]}
    # 10-01 E2E: 글자·단위 값 나열이 한 문자열로 묶여 로이드가 세 번 다시 불렀다
    assert sc.parse_targets(["S01=1만분의 475,1천분의 65,2026년 1월 1일", "S05=41만,659만", "S06=2041,2055"]) == {
        "S01": ["1만분의 475", "1천분의 65", "2026년 1월 1일"], "S05": ["41만", "659만"], "S06": ["2041", "2055"]}
    with pytest.raises(ValueError):
        sc.parse_targets(["16.5"])


def test_check_reports_found_missing_blocked_and_caches(monkeypatch, job, capsys):
    root, _ = job
    (root / "자료").mkdir()
    (root / "자료" / "메모.txt").write_text("내부 기준 42.0점", encoding="utf-8")
    sc = load("source_check", monkeypatch, root)
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        if url.endswith("/a"):
            # cp949 기사 — 인코딩을 맞혀야 찾는다
            return "<html><head><meta charset='euc-kr'></head><body><p>평균 16.5%로 나타났다</p></body></html>".encode(
                "cp949"), "text/html"
        raise OSError("404")

    monkeypatch.setattr(sc, "fetch", fake_fetch)
    code = sc.check(ID, {"S01": ["16.5", "99.9"], "S02": ["1"], "S03": ["7"], "S04": ["42.0"], "S09": ["1"]})
    out = capsys.readouterr().out
    assert code == 1
    assert "✓ 16.5 · 본문" in out and "【16.5】" in out
    assert "✗ 99.9" in out
    assert "못 열었다: OSError" in out                      # S02
    assert "열지 않음(E-056" in out and "pwc.com" not in "".join(fetched)  # S03은 받지 않는다
    assert "✓ 42.0" in out                                  # S04 로컬 자료
    assert "05 §5에 행 없음" in out                          # S09
    assert "결과: 못 찾음·못 엶 4건" in out

    # 다시 부르면 받아 둔 원문을 쓴다
    sc.check(ID, {"S01": ["16.5"]})
    assert fetched.count("https://example.com/a") == 1
    assert (root / "작업" / ID / "sources" / "_check" / "S01.html").is_file()


def test_pdf_source_reports_page(monkeypatch, job, capsys):
    root, _ = job
    fitz = pytest.importorskip("pymupdf")
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "page one 10.0")
    doc.new_page().insert_text((72, 72), "total 3,508 people")
    data = doc.tobytes()
    sc = load("source_check", monkeypatch, root)
    monkeypatch.setattr(sc, "fetch", lambda url: (data, "application/pdf"))
    assert sc.check(ID, {"S02": ["3508"]}) == 0
    assert "✓ 3508 · 쪽 2" in capsys.readouterr().out
    assert (root / "작업" / ID / "sources" / "_check" / "S02.pdf").is_file()


# --- render_doc ---------------------------------------------------------------


def test_render_doc_uses_latest_07_and_summarises(monkeypatch, job, capsys):
    root, ws = job
    (ws / "00_user_brief.md").write_text("# User Brief\n- 모드: DOCUMENT\n--- 헤더 끝 ---\n", encoding="utf-8")
    (ws / "07_final_document.md").write_text("# 옛 원고\n", encoding="utf-8")
    (ws / "07_final_document_v02.md").write_text("# 새 원고\n", encoding="utf-8")
    rd = load("render_doc", monkeypatch, root)
    calls = []

    def fake_run(*args):
        calls.append(args)
        tool = Path(args[0]).name
        if tool == "gate_check.py":
            return 1, "# gate\nFAIL  [출처] 블록 없음\nCHECK [강도] 때문에\nOK    [수치] 없음\nOK    [REMOVE] 없음\n\n결과: FAIL 1 · CHECK 1 — 담당에게"
        if tool == "md2html.py":
            Path(args[2]).write_text("<html></html>", encoding="utf-8")
            return 0, "경고: 그림 파일 없음: a.png\n경고: 그림 파일 없음: a.png\nHTML: x"
        return 0, "PDF: x\n크기: 1 바이트 / 페이지: 3\n임베드 폰트: P\n모아보기: c.png · 3 쪽\n검사 결과: OK"

    monkeypatch.setattr(rd, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["render_doc.py", ID, "--pages", "2"])
    assert rd.main() == 1  # 게이트 FAIL — 렌더는 하고 1을 돌려준다
    out = capsys.readouterr().out
    assert "07_final_document_v02.md" in out and Path(calls[1][1]).name == "07_final_document_v02.md"
    assert "FAIL  [출처]" in out and "CHECK [강도]" in out and "OK 2건 생략" in out and "OK    [수치]" not in out
    assert out.count("경고: 그림 파일 없음") == 1          # 같은 경고는 한 번
    assert "임베드 폰트" not in out and "검사 결과: OK" in out
    assert calls[2][-2:] == ("--pages", "2")


def test_render_doc_without_07_stops(monkeypatch, job):
    root, _ = job
    rd = load("render_doc", monkeypatch, root)
    monkeypatch.setattr(sys, "argv", ["render_doc.py", ID])
    assert rd.main() == 2


def test_gate_check_follows_work_root(job):
    """render_doc이 임시 루트에서 부르는 gate_check도 같은 루트의 작업을 본다."""
    root, ws = job
    (ws / "00_user_brief.md").write_text("# User Brief\n- 모드: DOCUMENT\n--- 헤더 끝 ---\n", encoding="utf-8")
    done = subprocess.run([sys.executable, str(TOOLS / "gate_check.py"), ID, "05"], capture_output=True, text=True,
                          encoding="utf-8", env={**os.environ, "DOCUMASTER_WORK_ROOT": str(root),
                                                 "PYTHONIOENCODING": "utf-8"}, check=False)
    assert "05_verified_research_pack.md" in done.stdout and "[중단]" not in done.stdout


def test_html_keeps_image_alt_text(monkeypatch, tmp_path):
    """관공서 공지는 본문을 그림으로 올리고 alt에 같은 글을 넣는다(10-01 E2E 국민연금공단)."""
    sc = load("source_check", monkeypatch, tmp_path)
    page = '<p><img src="a.jpg" alt="상한액:6,590,000원 하한액:410,000원"></p><img src="logo.svg">'
    text = sc.html_text(page.encode("utf-8"), "text/html; charset=utf-8")
    assert "6,590,000" in text and sc.pattern_of("659만").search(text)


def test_law_go_kr_shell_follows_to_article_body(monkeypatch, tmp_path):
    """법제처 lsInfoP는 조문 없는 껍데기다 — 같은 페이지의 efYd로 lsInfoR 본문을 받는다."""
    sc = load("source_check", monkeypatch, tmp_path)
    asked = []
    monkeypatch.setattr(sc, "fetch", lambda url: asked.append(url) or ("<p>1천분의 65</p>".encode(), "text/html"))
    shell = b"<script>var efYd = '20260101';</script>"
    data, _ = sc.follow_shell("https://www.law.go.kr/lsInfoP.do?lsiSeq=280269", shell, "text/html")
    assert asked == ["https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=280269&efYd=20260101"] and "1천분의".encode() in data
    # 다른 사이트는 그대로
    assert sc.follow_shell("https://example.com/lsInfoP.do?lsiSeq=1", shell, "t") == (shell, "t")


def test_gate_draft_skips_state_bookkeeping(job):
    """아냐의 자체 검사(--draft)는 로이드가 기록할 상태.md를 보지 않는다 — 매번 뜨던 FAIL 소음을 없앤다."""
    root, ws = job
    (ws / "00_user_brief.md").write_text("# User Brief\n- 모드: DOCUMENT\n--- 헤더 끝 ---\n", encoding="utf-8")
    (ws / "07_final_document.md").write_text("본문이다.[S01]\n\n::: sources 출처\nS01 | 자료 | 기관 | 2026 | https://e.x\n:::\n",
                                             encoding="utf-8")
    env = {**os.environ, "DOCUMASTER_WORK_ROOT": str(root), "PYTHONIOENCODING": "utf-8"}
    run = lambda *extra: subprocess.run([sys.executable, str(TOOLS / "gate_check.py"), ID, "07", *extra],  # noqa: E731
                                        capture_output=True, text=True, encoding="utf-8", env=env, check=False).stdout
    assert "상태.md가 없다" in run() and "상태 기록" not in run("--draft")
