"""HTML을 PDF로 굽고, 쪽번호를 찍고, 기계 검사를 한 번에 한다.

경로: md2html.py 로 만든 HTML → Edge 헤드리스 인쇄 → PyMuPDF 쪽번호 → 검사.
Edge 인쇄는 머리말·꼬리말을 넣지 않으므로 쪽번호는 PyMuPDF가 직접 찍는다.

사용:
    python .claude/tools/make_pdf.py <입력.html> <출력.pdf> [--label "문서명"] [--no-page-number]
                                     [--contact] [--pages 3,7]
    --contact    같은 폴더에 contact.png(전 쪽 모아보기, 4열)
    --pages 3,7  같은 폴더에 p03.png·p07.png(확대, 100dpi). PDF를 다시 굽지 않으려면 --only-images와 함께
    --only-images 이미 있는 PDF(NotebookLM 슬라이드 포함)에서 모아보기·확대만 만든다

대제목(h1) 아래 같은 쪽에 본문이 7줄 미만 남으면 그 장은 다음 쪽에서 시작하도록 HTML에 break-before를 넣고
다시 굽는다(문서규격 §4). 끄려면 --no-chapter-room.

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


CHAPTER_MIN_LINES = 7


def ensure_chapter_room(html_path, pdf_path):
    """대제목과 본문 CHAPTER_MIN_LINES줄을 한 쪽에 둘 수 없으면 그 장을 다음 쪽으로 넘긴다."""
    import html as htmllib
    import re
    import fitz
    with open(html_path, encoding="utf-8") as f:
        s = re.sub(r'<style id="chroom">.*?</style>', "", f.read(), flags=re.S)
    titles = []

    def mark(m):
        titles.append(htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip())
        return '<h1 id="ch%d">%s</h1>' % (len(titles) - 1, m.group(1))

    s = re.sub(r"<h1>(.*?)</h1>", mark, s, flags=re.S)  # 표지 제목(h1 class="title")은 제외
    if not titles:
        return []
    breaks = set()
    # 한 번에 하나씩 넘긴다 — 앞 장을 넘기면 뒤 장의 위치가 바뀌어, 같은 렌더로 함께 정하면 빈 쪽이 생긴다(10-02 삼위일체 5쪽)
    rounds = min(len(titles), 12)
    for round_no in range(rounds + 1):  # 마지막 회차는 정한 넘김을 반영해 굽기만 한다
        css = "".join("#ch%d{break-before:page;margin-top:0;}" % i for i in sorted(breaks))
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(s.replace("</head>", '<style id="chroom">%s</style></head>' % css, 1))
        print_pdf(html_path, pdf_path)
        doc = fitz.open(pdf_path)
        new = set()
        for i, t in enumerate(titles):
            if i in breaks:
                continue
            for page in doc:
                hits = [r for r in page.search_for(t[-9:]) if r.height > 14]  # 21pt 제목만(본문 인용 제외)
                if not hits:
                    continue
                y, bottom = hits[0].y1, page.rect.height - 45  # 꼬리말 위까지
                lines = [ln for b in page.get_text("dict")["blocks"] if b["type"] == 0
                         for ln in b["lines"]
                         if ln["bbox"][1] > y - 1 and ln["bbox"][3] < bottom and ln["spans"][0]["size"] < 12]
                if len(lines) < CHAPTER_MIN_LINES:
                    new.add(i)
                break
        doc.close()
        if not new or round_no == rounds:
            break
        breaks.add(min(new))
    if breaks:
        print("장 새 쪽 이동(본문 %d줄 미만):" % CHAPTER_MIN_LINES, ", ".join(titles[i][:12] for i in sorted(breaks)))
    return sorted(breaks)


def label_font():
    dirs = [r"C:\Windows\Fonts",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    # 이름을 바깥 루프로 — 맑은고딕(13MB)을 Pretendard보다 먼저 집으면 통째로 임베드된다(E-061)
    for name in ("Pretendard-Regular.ttf", "Pretendard-Regular.otf", "malgun.ttf"):
        for d in dirs:
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
    try:
        doc.subset_fonts()  # 라벨 폰트를 쓴 글자만 남긴다(fontTools 필요 — 없으면 통째로 남는다)
    except Exception as e:
        print("참고: 폰트 서브셋 생략 —", type(e).__name__)
    tmp = pdf_path + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
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


def save_images(pdf_path, contact, pages):
    """Render Gate용 이미지. 모아보기 한 장 + 의심 쪽 확대."""
    import io
    import fitz
    from PIL import Image
    out_dir = os.path.dirname(os.path.abspath(pdf_path))
    doc = fitz.open(pdf_path)
    if contact:
        # A4는 40dpi(약 330px 폭). 슬라이드처럼 넓은 쪽은 폭 400px로 묶는다 — 모아보기가 한 장에 읽히게
        ims = [Image.open(io.BytesIO(p.get_pixmap(matrix=fitz.Matrix(min(40 / 72, 400 / p.rect.width),
                                                                     min(40 / 72, 400 / p.rect.width))
                                                  ).tobytes("png"))) for p in doc]
        w, h = ims[0].size
        cols = 4
        sheet = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)), "white")
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(os.path.join(out_dir, "contact.png"))
        print("모아보기:", os.path.join(out_dir, "contact.png"), "·", doc.page_count, "쪽")
    for n in pages:
        if 1 <= n <= doc.page_count:
            path = os.path.join(out_dir, "p%02d.png" % n)
            doc[n - 1].get_pixmap(dpi=100).save(path)
            print("확대:", path)
    doc.close()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pages = []
    if "--pages" in sys.argv:
        raw = sys.argv[sys.argv.index("--pages") + 1]
        pages = [int(n) for n in raw.split(",") if n.strip().isdigit()]
        args = [a for a in args if a != raw]
    if "--only-images" in sys.argv and args:
        save_images(args[-1], "--contact" in sys.argv, pages)
        return 0
    if len(args) < 2:
        print(__doc__)
        return 2
    label = ""
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]
    if label in args:
        args.remove(label)
    html_path, pdf_path = args[0], args[1]

    print_pdf(html_path, pdf_path)
    if "--no-chapter-room" not in sys.argv:
        ensure_chapter_room(html_path, pdf_path)
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
    if not problems and ("--contact" in sys.argv or pages):
        save_images(pdf_path, "--contact" in sys.argv, pages)
    print("검사 결과:", "OK" if not problems else " / ".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
