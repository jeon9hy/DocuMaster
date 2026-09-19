"""HTML을 PDF로 굽고, 쪽번호를 찍고, 기계 검사를 한 번에 한다.

경로: md2html.py 로 만든 HTML → Edge 헤드리스 인쇄 → PyMuPDF 쪽번호 → 검사.
Edge 인쇄는 머리말·꼬리말을 넣지 않으므로 쪽번호는 PyMuPDF가 직접 찍는다.

사용:
    python .claude/tools/make_pdf.py <입력.html> <출력.pdf> [--label "문서명"] [--no-page-number]

출력 마지막 줄이 `검사 결과: OK` 가 아니면 그 PDF를 쓰지 않는다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge():
    for p in EDGE:
        if os.path.exists(p):
            return p
    return None


def to_url(path):
    return "file:///" + os.path.abspath(path).replace("\\", "/").replace(" ", "%20")


def print_pdf(html_path, pdf_path):
    edge = find_edge()
    if not edge:
        raise SystemExit("Edge를 찾지 못했다 — 이 PC의 인쇄 경로가 없다. 사용자에게 보고한다.")
    before = os.path.getmtime(pdf_path) if os.path.exists(pdf_path) else 0
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--print-to-pdf=" + os.path.abspath(pdf_path), to_url(html_path)]
    r = subprocess.run(cmd, capture_output=True, timeout=180)
    # Edge는 프로세스가 끝난 뒤에도 잠깐 뒤 PDF를 쓴다(환경기록 E-002).
    # 종료 코드만 보고 판단하지 않는다 — 파일이 실제로 새로 쓰였는지 최대 40초 기다린다.
    deadline = time.time() + 40
    while time.time() < deadline:
        if os.path.exists(pdf_path) and os.path.getmtime(pdf_path) > before:
            size = os.path.getsize(pdf_path)
            time.sleep(0.8)
            if os.path.getsize(pdf_path) == size and size > 0:
                return r.returncode
        time.sleep(0.8)
    tail = (r.stderr or b"").decode("utf-8", "replace")[-600:]
    raise SystemExit("인쇄 실패 — PDF가 새로 쓰이지 않았다. 이 파일을 쓰지 마라.\n" + tail)


def label_font():
    dirs = [r"C:\Windows\Fonts",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    for d in dirs:
        for name in ("Pretendard-Regular.ttf", "Pretendard-Regular.otf", "malgun.ttf"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def stamp_pages(pdf_path, label="", skip_first=False):
    import fitz
    doc = fitz.open(pdf_path)
    n = doc.page_count
    for i, page in enumerate(doc):
        if skip_first and i == 0:
            continue  # 표지에는 쪽번호·라벨을 찍지 않는다
        w, h = page.rect.width, page.rect.height
        page.insert_text((w / 2 - 12, h - 26), "%d / %d" % (i + 1, n),
                         fontsize=8, color=(0.42, 0.42, 0.45))
        if label:
            # 기본 폰트(Helvetica)는 한글을 "..." 로 떨군다(E-003). 내장 CJK 폰트("korea")는
            # 자간이 벌어져 보여서, 본문과 같은 Pretendard 파일이 있으면 그걸 쓴다(E-027).
            font = label_font()
            kw = {"fontname": "pret", "fontfile": font} if font else {"fontname": "korea"}
            page.insert_text((40, h - 26), label[:40], fontsize=7.5,
                             color=(0.55, 0.55, 0.58), **kw)
    tmp = pdf_path + ".tmp"
    doc.save(tmp)
    doc.close()
    os.replace(tmp, pdf_path)
    return n


def inspect(pdf_path):
    """기계 검사 — 빈 페이지·글자 수·잘림 의심을 센다."""
    import fitz
    doc = fitz.open(pdf_path)
    empty, chars = [], []
    for i, page in enumerate(doc):
        t = page.get_text().strip()
        chars.append(len(t))
        if len(t) < 30:
            empty.append(i + 1)
    fonts = sorted({f[3] for i in range(doc.page_count)
                    for f in doc[i].get_fonts(full=True)})
    doc.close()
    return {"pages": len(chars), "empty": empty, "chars": sum(chars),
            "min_chars": min(chars) if chars else 0, "fonts": fonts}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    label = ""
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]
    html_path, pdf_path = args[0], args[1]

    print_pdf(html_path, pdf_path)
    if "--no-page-number" not in sys.argv:
        with open(html_path, encoding="utf-8") as f:
            has_cover = '<meta name="doc-cover" content="1">' in f.read(4000)
        stamp_pages(pdf_path, label, skip_first=has_cover)
    info = inspect(pdf_path)
    print("PDF:", os.path.abspath(pdf_path))
    print("크기:", os.path.getsize(pdf_path), "바이트 / 페이지:", info["pages"])
    print("본문 글자 수 합계:", info["chars"], "/ 최소 페이지 글자 수:", info["min_chars"])
    print("임베드 폰트:", ", ".join(info["fonts"]) or "(없음)")
    problems = []
    if info["pages"] == 0:
        problems.append("페이지가 0이다")
    if info["empty"]:
        problems.append("사실상 빈 페이지: %s" % info["empty"])
    if info["chars"] < 200:
        problems.append("본문 글자가 거의 없다 — 변환이 깨졌을 수 있다")
    print("검사 결과:", "OK" if not problems else " / ".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
