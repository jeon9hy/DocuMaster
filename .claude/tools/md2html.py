"""마크다운 원고를 인쇄용 HTML로 변환한다. 외부 라이브러리를 쓰지 않는다.

왜 자체 변환기인가 — 이 PC에는 pandoc·markdown·weasyprint가 없다(환경기록 E-001).
설치를 요구하는 대신, 보고서에 실제로 쓰는 문법만 지원하는 작은 변환기를 둔다.

기본 문법: # ~ #### / 문단 / - * + 불릿(2단계) / 1. 번호 / 표(정렬) / > 인용 /
      --- 수평선 / **굵게** *기울임* `코드` [링크](url) / ``` 코드블록 ``` /
      <!-- pagebreak --> 페이지 나눔

편집 디자인 문법 (E-027 — 문서도 디자인을 한다. 전체 설명은 `아냐/문서작성.md` §2):
  front matter  맨 위 `---` 블록: title · subtitle · kind · date · org · accent · accent2 ·
                cover(true/false) · cover_image · cover_credit
  ![캡션](경로 "크레디트")   그림 — 원고 파일 기준 상대경로. PDF 안에 넣어 굽는다
  ```chart       막대(bar)·세로막대(column)·선(line) 차트 → SVG
  ```timeline    시점 | 사건 | 부연
  ```flow        단계 | 부연   (가로 흐름도)
  ::: summary [제목]  핵심 요약 패널
  ::: stats           값 | 라벨 | 조건  (핵심 수치 띠, 2~4개)
  ::: note            Qualification — 바로 앞 주장에 붙는 짧은 한계 문구
  ::: quote [출처]     풀쿼트
  ::: sources 출처     S01 | 자료명 | 발행 주체 | 날짜 | 링크 또는 위치
  자료: / 출처: / 주:  로 시작하는 문단 → 작은 캡션

사용:
    python .claude/tools/md2html.py <입력.md> <출력.html> [--title "문서 제목"]
"""
from __future__ import annotations

import base64
import html
import math
import mimetypes
import os
import re
import sys

# ── 테마 ────────────────────────────────────────────────────────────────────
# 레이아웃 체계는 고정하고, 주제에서 나오는 것(accent·표지)만 문서마다 바꾼다.
# accent가 없으면 중립 잉크로 떨어진다 — 이건 기본 스타일이 아니라 "미지정" 상태다.
DEFAULT_ACCENT = "#3A4A5C"
# 다계열 선 차트용 — dataviz 기준 팔레트의 앞 세 슬롯(모든 쌍 검증 통과, 밝은 배경).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
NEUTRAL_MARK = "#C9CDD3"

CSS = """
@page { size: A4; margin: 20mm 19mm 22mm 19mm; }
@page cover { margin: 0; }
:root {
  --ink: #16181d; --ink-2: #474c56; --muted: #7b808b;
  --rule: #d6d9de; --hair: #e9ebee; --paper: #ffffff;
  --accent: %(accent)s; --accent-2: %(accent2)s;
  --accent-soft: color-mix(in srgb, var(--accent) 7%%, white);
  --accent-deep: color-mix(in srgb, var(--accent) 80%%, black);
}
* { box-sizing: border-box; }
body {
  font-family: "Pretendard", "Malgun Gothic", sans-serif;
  font-size: 10.4pt; line-height: 1.78; color: var(--ink); margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
  word-break: keep-all; overflow-wrap: break-word;
}

/* 표지 — 사진이 없으면 전면 색 표지, 있으면 위 사진 + 아래 제목 */
.cover { page: cover; height: 297mm; position: relative; overflow: hidden;
         page-break-after: always; }
.cover.solid { background: var(--accent); color: white; }
.cover.photo { background: var(--paper); }
.cover .photo-img { position: absolute; left: 0; top: 0; width: 100%%; height: 158mm;
                    background-size: cover; background-position: center; }
.cover .credit { position: absolute; top: 161mm; right: 19mm; font-size: 7pt; color: var(--muted); }
.cover .kind { position: absolute; top: 22mm; left: 21mm; font-size: 9pt; font-weight: 600;
               letter-spacing: .14em; }
.cover.solid .kind { color: rgba(255,255,255,.78); }
.cover.photo .kind { color: white; text-shadow: 0 0 6px rgba(0,0,0,.35); }
.cover .body { position: absolute; left: 21mm; right: 24mm; }
.cover.solid .body { top: 96mm; }
.cover.photo .body { top: 176mm; }
.cover .rule { width: 18mm; height: 2.2pt; margin-bottom: 14pt; }
.cover.solid .rule { background: rgba(255,255,255,.9); }
.cover.photo .rule { background: var(--accent); }
.cover h1.title { font-size: 32pt; line-height: 1.26; letter-spacing: -0.035em; margin: 0 0 16pt;
                  border: 0; padding: 0; color: inherit; }
.cover.photo h1.title { color: var(--ink); }
.cover .subtitle { font-size: 12.5pt; line-height: 1.65; margin: 0; max-width: 145mm; }
.cover.solid .subtitle { color: rgba(255,255,255,.86); }
.cover.photo .subtitle { color: var(--ink-2); }
.cover .meta { position: absolute; left: 21mm; right: 21mm; bottom: 22mm; font-size: 9pt;
               padding-top: 8pt; display: flex; justify-content: space-between; }
.cover.solid .meta { color: rgba(255,255,255,.75); border-top: 0.6pt solid rgba(255,255,255,.35); }
.cover.photo .meta { color: var(--muted); border-top: 0.6pt solid var(--rule); }

/* 제목 */
h1 { font-size: 21pt; line-height: 1.32; margin: 0 0 16pt; letter-spacing: -0.03em; }
h2 { font-size: 15pt; line-height: 1.4; margin: 26pt 0 10pt; letter-spacing: -0.02em;
     page-break-after: avoid; break-after: avoid; page-break-inside: avoid; break-inside: avoid; }
h2 .no { display: block; font-size: 9pt; font-weight: 700; letter-spacing: .14em;
         color: var(--accent); margin-bottom: 3pt; }
h2.chapter { padding-top: 10pt; border-top: 1.2pt solid var(--ink); }
h3 { font-size: 11.6pt; margin: 18pt 0 6pt; color: var(--accent-deep);
     page-break-after: avoid; break-after: avoid; }
h4 { font-size: 10.4pt; margin: 12pt 0 4pt; color: var(--ink-2); page-break-after: avoid; }

p { margin: 0 0 8.5pt; text-align: left; }
p.src { font-size: 8pt; color: var(--muted); margin: -2pt 0 12pt; line-height: 1.5; }
ul, ol { margin: 0 0 9pt; padding-left: 17pt; }
li { margin-bottom: 3pt; }
li::marker { color: var(--accent); }
li > ul, li > ol { margin: 3pt 0 0; }
strong { font-weight: 700; }
a { color: var(--accent-deep); text-decoration: none; border-bottom: 0.4pt solid var(--rule); }
sup.cite { font-size: 7.5pt; line-height: 0; margin-left: 1pt; }
sup.cite a { border: 0; font-weight: 700; }
hr { border: none; border-top: 0.6pt solid var(--rule); margin: 18pt 0; }
.pagebreak { page-break-before: always; }
code { font-family: "Consolas", monospace; font-size: 8.8pt; background: #f2f3f5;
       padding: 0.5pt 3pt; border-radius: 2pt; }
pre { background: #f6f7f8; border-radius: 3pt; padding: 8pt 10pt; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.4pt; line-height: 1.5; }

/* 표 — 세로선 없이 가로 괘선만 */
table { border-collapse: collapse; width: 100%%; margin: 12pt 0 6pt; font-size: 9.3pt;
        page-break-inside: avoid; line-height: 1.55; }
thead th { border-bottom: 1.2pt solid var(--ink); font-weight: 700; text-align: left;
           padding: 5pt 7pt 5pt 0; vertical-align: bottom; }
td { border-bottom: 0.5pt solid var(--hair); padding: 5pt 7pt 5pt 0; vertical-align: top; }
tbody tr:last-child td { border-bottom: 0.8pt solid var(--rule); }
td[style*="right"], th[style*="right"] { font-variant-numeric: tabular-nums; }

/* 인용 */
blockquote { margin: 12pt 0; padding: 2pt 0 2pt 12pt; border-left: 2pt solid var(--accent);
             color: var(--ink-2); }
blockquote p:last-child { margin-bottom: 0; }

/* 핵심 요약 */
.summary { background: var(--accent-soft); padding: 13pt 16pt 7pt; margin: 6pt 0 16pt;
           page-break-inside: avoid; }
.summary .label { font-size: 8.5pt; font-weight: 700; letter-spacing: .12em; color: var(--accent-deep);
                  margin-bottom: 6pt; }
.summary ul, .summary ol { padding-left: 15pt; }

/* 핵심 수치 띠 */
.stats { display: grid; gap: 0; margin: 14pt 0 16pt; page-break-inside: avoid;
         border-top: 1.2pt solid var(--ink); }
.stats .stat { padding: 9pt 12pt 8pt 0; }
.stats .stat + .stat { padding-left: 12pt; border-left: 0.5pt solid var(--rule); }
.stats .v { font-size: 25pt; font-weight: 700; letter-spacing: -0.03em; line-height: 1.15;
            color: var(--accent-deep); }
.stats .l { font-size: 9.5pt; font-weight: 600; margin-top: 3pt; }
.stats .c { font-size: 8pt; color: var(--muted); line-height: 1.45; margin-top: 2pt; }

/* Qualification */
.note { font-size: 8.8pt; color: var(--ink-2); line-height: 1.6; margin: -2pt 0 12pt;
        padding-left: 10pt; border-left: 1.5pt solid var(--accent-2); }
.note p { margin: 0 0 3pt; }

/* 풀쿼트 */
.pull { margin: 18pt 0 18pt; page-break-inside: avoid; }
.pull .q { font-size: 15pt; line-height: 1.5; font-weight: 600; letter-spacing: -0.02em;
           color: var(--ink); }
.pull .q::before { content: "\\201C"; display: block; font-size: 30pt; line-height: .9;
                   color: var(--accent); }
.pull .by { font-size: 8.5pt; color: var(--muted); margin-top: 6pt; }

/* 출처 */
.sources { margin-top: 24pt; padding-top: 10pt; border-top: 1.2pt solid var(--ink); }
.sources h2 { margin-top: 0; }
.source-row { display: grid; grid-template-columns: 18pt 1fr; gap: 6pt; padding: 5pt 0;
              border-bottom: 0.5pt solid var(--hair); break-inside: avoid; page-break-inside: avoid;
              font-size: 8.4pt; line-height: 1.5; }
.source-no { color: var(--accent-deep); font-weight: 700; }
.source-meta { color: var(--ink-2); }

/* 그림 */
figure { margin: 14pt 0 14pt; page-break-inside: avoid; }
figure img { width: 100%%; display: block; }
figure.narrow img { width: 62%%; }
figcaption { font-size: 8.6pt; color: var(--ink-2); margin-top: 6pt; line-height: 1.5; }
figcaption .credit { color: var(--muted); }
.chart-title { font-size: 10pt; font-weight: 700; margin-bottom: 1pt; }
.chart-sub { font-size: 8.5pt; color: var(--muted); margin-bottom: 4pt; }
svg.chart { width: 100%%; height: auto; display: block; font-family: "Pretendard", sans-serif; }

/* 타임라인 */
.timeline { margin: 12pt 0 14pt; padding: 0; list-style: none; page-break-inside: avoid; }
.timeline li { position: relative; padding: 0 0 11pt 20pt; margin: 0; }
.timeline li::before { content: ""; position: absolute; left: 3.5pt; top: 6pt; bottom: -6pt;
                       width: 0.8pt; background: var(--rule); }
.timeline li:last-child::before { display: none; }
.timeline li::after { content: ""; position: absolute; left: 0; top: 4.5pt; width: 8pt; height: 8pt;
                      border-radius: 50%%; background: var(--accent); box-shadow: 0 0 0 2pt white; }
.timeline .t { font-size: 8.8pt; font-weight: 700; color: var(--accent-deep);
               font-variant-numeric: tabular-nums; }
.timeline .e { font-weight: 600; }
.timeline .d { font-size: 9pt; color: var(--ink-2); line-height: 1.55; }

/* 흐름도 */
.flow { display: flex; align-items: stretch; margin: 14pt 0 16pt; page-break-inside: avoid; }
.flow .step { flex: 1 1 0; padding: 8pt 8pt 0 0; border-top: 2pt solid var(--accent); }
.flow .step .n { font-size: 8pt; font-weight: 700; color: var(--accent); letter-spacing: .1em; }
.flow .step .h { font-weight: 700; font-size: 10pt; line-height: 1.4; margin-top: 2pt; }
.flow .step .d { font-size: 8.6pt; color: var(--ink-2); line-height: 1.5; margin-top: 3pt; }
.flow .arrow { flex: 0 0 14pt; color: var(--muted); font-size: 11pt; padding-top: 12pt; text-align: center; }
"""

RE_CODE = re.compile(r"`([^`]+)`")
RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
RE_EM = re.compile(r"(?<![\*\w])\*([^\*\n]+)\*(?!\*)")
RE_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\)\s]+)\)")
RE_CITATION = re.compile(r"\[S(\d{2,3})\]")
RE_IMG = re.compile(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)(\{narrow\})?$')
RE_SRC = re.compile(r"^(자료|출처|주)\s*[:：]")

BASE_DIR = "."
WARNINGS: list[str] = []


def inline(text):
    """인라인 문법을 HTML로. 코드 조각은 먼저 빼 두어 굵게/링크 치환에 오염되지 않게 한다."""
    out = html.escape(text)
    kept = []

    def stash(m):
        kept.append("<code>" + m.group(1) + "</code>")
        return "\x00%d\x00" % (len(kept) - 1)

    out = RE_CODE.sub(stash, out)
    out = RE_BOLD.sub(r"<strong>\1</strong>", out)
    out = RE_EM.sub(r"<em>\1</em>", out)
    out = RE_LINK.sub(r'<a href="\2">\1</a>', out)
    out = RE_CITATION.sub(lambda m: '<sup class="cite"><a href="#source-S%s">%d</a></sup>'
                          % (m.group(1), int(m.group(1))), out)
    for i, s in enumerate(kept):
        out = out.replace("\x00%d\x00" % i, s)
    return out


def align_of(cell):
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return ' style="text-align:center"'
    if cell.endswith(":"):
        return ' style="text-align:right"'
    return ""


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


# ── 색 검사 ─────────────────────────────────────────────────────────────────


def _lum(hexc):
    hexc = hexc.lstrip("#")
    if len(hexc) == 3:
        hexc = "".join(c * 2 for c in hexc)
    rgb = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b="#ffffff"):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def valid_hex(v):
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", v or ""))


# ── 그림 ────────────────────────────────────────────────────────────────────


def embed(path):
    full = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    if not os.path.exists(full):
        WARNINGS.append("그림 파일 없음: %s" % path)
        return None
    mime = mimetypes.guess_type(full)[0] or "image/png"
    with open(full, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def figure(cap, path, credit, narrow):
    src = embed(path)
    if not src:
        return '<p class="src">[그림 누락: %s]</p>' % html.escape(path)
    cred = ' <span class="credit">%s</span>' % inline(credit) if credit else ""
    return ('<figure%s><img src="%s" alt="%s"><figcaption>%s%s</figcaption></figure>'
            % (' class="narrow"' if narrow else "", src, html.escape(cap), inline(cap), cred))


# ── 차트 (정적 SVG) ─────────────────────────────────────────────────────────
# 마크 규격은 dataviz 기준: 막대 ≤24px·데이터 끝 4px 라운드·기준선 쪽은 직각,
# 선 2px, 끝점 r4 + 흰 테두리 2px, 격자선 헤어라인 실선, 글자는 계열색을 입지 않는다.


def parse_spec(body):
    spec, data, in_data = {}, [], False
    for raw in body:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if in_data:
            data.append(split_row(line))
            continue
        m = re.match(r"^(\w+)\s*:\s*(.*)$", line)
        if m and m.group(1) == "data":
            in_data = True
            continue
        if m:
            spec[m.group(1)] = m.group(2).strip()
    return spec, data


def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def fmt(v, unit=""):
    s = ("{:,.0f}" if abs(v - round(v)) < 1e-9 else "{:,.1f}").format(v)
    return s + unit


def text_w(s, size):
    """대략적 글자 폭 — 한글은 1em, 라틴·숫자는 0.58em."""
    return sum(size if ord(c) > 0x2E80 else size * 0.58 for c in s)


def nice_ticks(vmax, n=4):
    if vmax <= 0:
        return [0, 1]
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    top = math.ceil(vmax / step) * step
    return [i * step for i in range(int(round(top / step)) + 1)]


def svg_text(x, y, s, size=11, fill="#474c56", anchor="start", weight=400):
    return ('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s" font-weight="%d">%s</text>'
            % (x, y, size, fill, anchor, weight, html.escape(s)))


def bar_path_h(x0, x1, y, h, r=4):
    r = min(r, max(x1 - x0, 0), h / 2)
    return ("M%.1f %.1fH%.1fQ%.1f %.1f %.1f %.1fV%.1fQ%.1f %.1f %.1f %.1fH%.1fZ"
            % (x0, y, x1 - r, x1, y, x1, y + r, y + h - r, x1, y + h, x1 - r, y + h, x0))


def bar_path_v(x, y1, w, y0, r=4):
    r = min(r, max(y0 - y1, 0), w / 2)
    return ("M%.1f %.1fV%.1fQ%.1f %.1f %.1f %.1fH%.1fQ%.1f %.1f %.1f %.1fV%.1fZ"
            % (x, y0, y1 + r, x, y1, x + r, y1, x + w - r, x + w, y1, x + w, y1 + r, y0))


def chart_bar(spec, data, accent):
    unit = spec.get("unit", "")
    hl = [h.strip() for h in spec.get("highlight", "").split("|") if h.strip()]
    rows = [(r[0], num(r[1])) for r in data if len(r) >= 2 and num(r[1]) is not None]
    if not rows:
        return None
    W, row_h, bar_h = 640, 34, 18
    lab_w = min(max(text_w(l, 11.5) for l, _ in rows) + 14, 230)
    val_w = max(text_w(fmt(v, unit), 11.5) for _, v in rows) + 12
    x0, x_max = lab_w, W - val_w
    vmax = max(v for _, v in rows) or 1
    H = row_h * len(rows) + 6
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img">' % (W, H)]
    out.append('<line x1="%.1f" y1="0" x2="%.1f" y2="%d" stroke="#d6d9de" stroke-width="1"/>' % (x0, x0, H - 4))
    for i, (lab, v) in enumerate(rows):
        y = i * row_h + (row_h - bar_h) / 2
        x1 = x0 + (x_max - x0) * v / vmax
        on = (not hl) or lab in hl
        out.append('<path d="%s" fill="%s"/>' % (bar_path_h(x0, x1, y, bar_h), accent if on else NEUTRAL_MARK))
        out.append(svg_text(x0 - 10, y + bar_h - 4.5, lab, 11.5, "#16181d" if on else "#474c56", "end",
                            600 if (hl and on) else 400))
        out.append(svg_text(x1 + 7, y + bar_h - 4.5, fmt(v, unit), 11.5, "#16181d", "start",
                            700 if (hl and on) else 500))
    out.append("</svg>")
    return "".join(out)


def chart_column(spec, data, accent):
    unit = spec.get("unit", "")
    hl = [h.strip() for h in spec.get("highlight", "").split("|") if h.strip()]
    rows = [(r[0], num(r[1])) for r in data if len(r) >= 2 and num(r[1]) is not None]
    if not rows:
        return None
    W, H, top, bottom = 640, 250, 24, 34
    band = W / len(rows)
    bw = min(24, band * 0.6)
    vmax = max(v for _, v in rows) or 1
    y0 = H - bottom
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img">' % (W, H)]
    out.append('<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="#b9bdc4" stroke-width="1"/>' % (y0, W, y0))
    for i, (lab, v) in enumerate(rows):
        cx = band * i + band / 2
        y1 = y0 - (y0 - top) * v / vmax
        on = (not hl) or lab in hl
        out.append('<path d="%s" fill="%s"/>' % (bar_path_v(cx - bw / 2, y1, bw, y0), accent if on else NEUTRAL_MARK))
        out.append(svg_text(cx, y1 - 7, fmt(v, unit), 11, "#16181d", "middle", 700 if (hl and on) else 500))
        out.append(svg_text(cx, y0 + 18, lab, 11, "#474c56", "middle"))
    out.append("</svg>")
    return "".join(out)


def chart_line(spec, data, accent):
    unit = spec.get("unit", "")
    names = [s.strip() for s in spec.get("series", "").split("|") if s.strip()]
    rows = [r for r in data if len(r) >= 2]
    if not rows:
        return None
    k = max(len(r) for r in rows) - 1
    names = (names + ["계열 %d" % (j + 1) for j in range(k)])[:k]
    if k > 3:
        WARNINGS.append("선 차트 계열이 %d개 — 3개까지만 그린다. 나머지는 다른 그림으로 나눈다" % k)
        k, names = 3, names[:3]
    colors = [accent] if k == 1 else SERIES[:k]
    vals = [[num(r[j + 1]) if j + 1 < len(r) else None for r in rows] for j in range(k)]
    vmax = max(v for s in vals for v in s if v is not None) or 1
    ticks = nice_ticks(vmax)
    W, H, left, right, top, bottom = 640, 250, 46, 70, 16, 30
    y0, pw = H - bottom, W - left - right
    xs = [left + (pw * i / (len(rows) - 1) if len(rows) > 1 else pw / 2) for i in range(len(rows))]

    def yv(v):
        return y0 - (y0 - top) * v / ticks[-1]

    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img">' % (W, H)]
    for t in ticks:
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                   % (left, yv(t), W - right, yv(t), "#b9bdc4" if t == 0 else "#e9ebee"))
        out.append(svg_text(left - 8, yv(t) + 4, fmt(t), 10, "#7b808b", "end"))
    step = max(1, math.ceil(len(rows) / 8))
    for i, r in enumerate(rows):
        if i % step == 0 or i == len(rows) - 1:
            out.append(svg_text(xs[i], y0 + 18, r[0], 10, "#7b808b", "middle"))
    for j in range(k):
        pts = [(xs[i], yv(v)) for i, v in enumerate(vals[j]) if v is not None]
        if not pts:
            continue
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" '
                   'stroke-linejoin="round" stroke-linecap="round"/>'
                   % (" ".join("%.1f,%.1f" % p for p in pts), colors[j]))
        lx, ly = pts[-1]
        last = [v for v in vals[j] if v is not None][-1]
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="white" stroke-width="2"/>' % (lx, ly, colors[j]))
        out.append(svg_text(lx + 9, ly + 4, fmt(last, unit), 11, "#16181d", "start", 600))
    out.append("</svg>")
    legend = ""
    if k >= 2:
        legend = '<div class="chart-sub">' + " &nbsp; ".join(
            '<span style="display:inline-block;width:14px;height:2px;background:%s;vertical-align:middle;margin-right:4px"></span>%s'
            % (colors[j], html.escape(names[j])) for j in range(k)) + "</div>"
    return legend + "".join(out)


def render_chart(body, accent):
    spec, data = parse_spec(body)
    kind = spec.get("type", "bar")
    fn = {"bar": chart_bar, "column": chart_column, "line": chart_line}.get(kind)
    if not fn:
        WARNINGS.append("모르는 차트 type: %s" % kind)
        return ""
    svg = fn(spec, data, accent)
    if not svg:
        WARNINGS.append("차트에 숫자 데이터가 없다: %s" % spec.get("title", "(제목 없음)"))
        return ""
    head = ""
    if spec.get("title"):
        head += '<div class="chart-title">%s</div>' % inline(spec["title"])
    sub = " · ".join(x for x in (spec.get("unit") and "단위: " + spec["unit"], spec.get("note")) if x)
    if sub:
        head += '<div class="chart-sub">%s</div>' % inline(sub)
    cap = '<figcaption><span class="credit">%s</span></figcaption>' % inline(spec["source"]) if spec.get("source") else ""
    if not spec.get("source"):
        WARNINGS.append("차트에 source 가 없다: %s" % spec.get("title", "(제목 없음)"))
    return "<figure>%s%s%s</figure>" % (head, svg, cap)


def render_timeline(body):
    items = []
    for raw in body:
        if not raw.strip():
            continue
        c = split_row(raw)
        t, e, d = (c + ["", "", ""])[:3]
        items.append('<li><div class="t">%s</div><div class="e">%s</div>%s</li>'
                     % (inline(t), inline(e), '<div class="d">%s</div>' % inline(d) if d else ""))
    return '<ul class="timeline">%s</ul>' % "".join(items)


def render_flow(body):
    steps = [split_row(r) for r in body if r.strip()]
    parts = []
    for i, c in enumerate(steps):
        h, d = (c + ["", ""])[:2]
        if i:
            parts.append('<div class="arrow">→</div>')
        parts.append('<div class="step"><div class="n">%02d</div><div class="h">%s</div>%s</div>'
                     % (i + 1, inline(h), '<div class="d">%s</div>' % inline(d) if d else ""))
    if len(steps) > 5:
        WARNINGS.append("흐름도 단계가 %d개 — 5개를 넘으면 좁아진다" % len(steps))
    return '<div class="flow">%s</div>' % "".join(parts)


def render_block(kind, title, body, accent):
    if kind == "summary":
        return ('<div class="summary"><div class="label">%s</div>%s</div>'
                % (html.escape(title or "핵심 요약"), convert("\n".join(body), accent)))
    if kind == "stats":
        cells = []
        for raw in body:
            if not raw.strip():
                continue
            c = split_row(raw)
            v, lab, cond = (c + ["", "", ""])[:3]
            cells.append('<div class="stat"><div class="v">%s</div><div class="l">%s</div>%s</div>'
                         % (inline(v), inline(lab), '<div class="c">%s</div>' % inline(cond) if cond else ""))
        if len(cells) > 4:
            WARNINGS.append("stats 가 %d개 — 4개까지가 한 줄에 들어간다" % len(cells))
        return ('<div class="stats" style="grid-template-columns:repeat(%d,1fr)">%s</div>'
                % (max(len(cells), 1), "".join(cells)))
    if kind == "note":
        return '<div class="note">%s</div>' % convert("\n".join(body), accent)
    if kind == "quote":
        q = " ".join(l.strip() for l in body if l.strip())
        by = '<div class="by">— %s</div>' % inline(title) if title else ""
        return '<div class="pull"><div class="q">%s</div>%s</div>' % (inline(q), by)
    if kind == "sources":
        rows = []
        for raw in body:
            if not raw.strip():
                continue
            cells = split_row(raw)
            if len(cells) < 5 or not re.fullmatch(r"S\d{2,3}", cells[0]):
                WARNINGS.append("출처 행 형식 오류: %s" % raw.strip()[:80])
                continue
            source_id = cells[0]
            meta = " · ".join(cell for cell in cells[1:] if cell)
            rows.append('<div class="source-row" id="source-%s"><div class="source-no">%d</div>'
                        '<div class="source-meta">%s</div></div>'
                        % (source_id, int(source_id[1:]), inline(meta)))
        if not rows:
            WARNINGS.append("sources 블록에 올바른 출처 행이 없다")
        return '<section class="sources"><h2>%s</h2>%s</section>' % (
            html.escape(title or "출처"), "".join(rows))
    WARNINGS.append("모르는 블록: ::: %s" % kind)
    return convert("\n".join(body), accent)


# ── 본문 변환 ───────────────────────────────────────────────────────────────


def convert(md, accent=DEFAULT_ACCENT):
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    stack = []
    i = 0

    def close_lists(depth=0):
        while len(stack) > depth:
            out.append("</%s>" % stack.pop()[0])

    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()

        if s.startswith("<!--") and "pagebreak" in s:
            close_lists()
            out.append('<div class="pagebreak"></div>')
            i += 1
            continue

        if s.startswith("```"):
            close_lists()
            lang = s[3:].strip().lower()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            if lang == "chart":
                out.append(render_chart(buf, accent))
            elif lang == "timeline":
                out.append(render_timeline(buf))
            elif lang == "flow":
                out.append(render_flow(buf))
            else:
                out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(buf)))
            continue

        m = re.match(r"^:::\s*(\w+)\s*(.*)$", s)
        if m:
            close_lists()
            kind, title = m.group(1), m.group(2).strip()
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() != ":::":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(render_block(kind, title, buf, accent))
            continue

        if not s:
            close_lists()
            i += 1
            continue

        m = RE_IMG.match(s)
        if m:
            close_lists()
            out.append(figure(m.group(1), m.group(2), m.group(3), bool(m.group(4))))
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            close_lists()
            lvl, text = len(m.group(1)), m.group(2)
            nm = re.match(r"^(\d+)\.\s+(.*)$", text) if lvl == 2 else None
            if nm:
                out.append('<h2 class="chapter"><span class="no">%s</span>%s</h2>'
                           % (nm.group(1).zfill(2), inline(nm.group(2))))
            else:
                out.append("<h%d>%s</h%d>" % (lvl, inline(text), lvl))
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        if (s.startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1])):
            close_lists()
            head = split_row(s)
            aligns = [align_of(c) for c in split_row(lines[i + 1])]
            aligns += [""] * (len(head) - len(aligns))
            out.append("<table><thead><tr>")
            for j, c in enumerate(head):
                out.append("<th%s>%s</th>" % (aligns[j], inline(c)))
            out.append("</tr></thead><tbody>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                out.append("<tr>")
                for j, c in enumerate(split_row(lines[i])):
                    a = aligns[j] if j < len(aligns) else ""
                    out.append("<td%s>%s</td>" % (a, inline(c)))
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        if s.startswith(">"):
            close_lists()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            # 줄바꿈을 살린다 — 여러 줄 인용이 한 줄로 뭉개지던 문제
            out.append("<blockquote><p>%s</p></blockquote>" % "<br>".join(inline(b) for b in buf if b))
            continue

        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            indent = len(m.group(1).expandtabs(4))
            tag = "ul" if m.group(2) in "-*+" else "ol"
            depth = 1 if indent < 2 else 2
            close_lists(depth)
            if len(stack) < depth:
                out.append("<%s>" % tag)
                stack.append((tag, indent))
            elif stack[-1][0] != tag:
                out.append("</%s>" % stack.pop()[0])
                out.append("<%s>" % tag)
                stack.append((tag, indent))
            out.append("<li>%s</li>" % inline(m.group(3)))
            i += 1
            continue

        close_lists()
        buf = [s]
        i += 1
        while i < len(lines):
            n = lines[i].strip()
            if (not n or n.startswith(("#", "|", ">", "<!--", ":::", "![")
                                        ) or n.startswith("```")
                    or re.match(r"^([-*+]|\d+\.)\s+", n)
                    or re.match(r"^(-{3,}|\*{3,}|_{3,})$", n)):
                break
            buf.append(n)
            i += 1
        cls = ' class="src"' if RE_SRC.match(s) else ""
        out.append("<p%s>%s</p>" % (cls, inline(" ".join(buf))))

    close_lists()
    return "\n".join(out)


# ── 문서 ────────────────────────────────────────────────────────────────────


def front_matter(md):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md.replace("\r\n", "\n"), re.S)
    if not m:
        return {}, md
    meta = {}
    for line in m.group(1).split("\n"):
        kv = re.match(r"^(\w+)\s*:\s*(.*)$", line.strip())
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip('"')
    return meta, md.replace("\r\n", "\n")[m.end():]


def cover_html(meta):
    img = embed(meta["cover_image"]) if meta.get("cover_image") else None
    photo = '<div class="photo-img" style="background-image:url(%s)"></div>' % img if img else ""
    credit = '<div class="credit">%s</div>' % inline(meta["cover_credit"]) if img and meta.get("cover_credit") else ""
    kind = '<div class="kind">%s</div>' % html.escape(meta["kind"]) if meta.get("kind") else ""
    sub = '<p class="subtitle">%s</p>' % inline(meta["subtitle"]) if meta.get("subtitle") else ""
    left = html.escape(meta.get("org", ""))
    right = html.escape(meta.get("date", ""))
    return ('<section class="cover %s">%s%s%s<div class="body"><div class="rule"></div>'
            '<h1 class="title">%s</h1>%s</div>'
            '<div class="meta"><span>%s</span><span>%s</span></div></section>'
            % ("photo" if img else "solid", photo, credit, kind,
               inline(meta.get("title", "")), sub, left, right))


def main():
    global BASE_DIR
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    title = ""
    if "--title" in sys.argv:
        title = sys.argv[sys.argv.index("--title") + 1]
    BASE_DIR = os.path.dirname(os.path.abspath(args[0]))
    md = open(args[0], encoding="utf-8").read()
    meta, md = front_matter(md)

    accent = meta.get("accent", "")
    if accent and not valid_hex(accent):
        WARNINGS.append("accent 형식이 #RRGGBB 가 아니다: %s — 기본값으로 대체" % accent)
        accent = ""
    if not accent:
        accent = DEFAULT_ACCENT
        if meta:
            WARNINGS.append("accent 미지정 — 06B의 Art Direction 색을 front matter에 넣는다")
    if contrast(accent) < 3.0:
        WARNINGS.append("accent %s 의 흰 배경 대비가 %.2f:1 — 3:1 미만. 글자·가는 선이 안 보인다" % (accent, contrast(accent)))
    accent2 = meta.get("accent2", "")
    accent2 = accent2 if valid_hex(accent2) else accent

    title = title or meta.get("title", "")
    if not title:
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else "문서"
    cover = meta.get("cover", "true" if meta.get("title") else "false").lower() == "true"
    if cover:
        meta.setdefault("title", title)
        # 표지가 제목을 맡으면 본문 첫 H1은 뺀다
        md = re.sub(r"^#\s+.+\n", "", md, count=1, flags=re.M)
    elif meta.get("title") and not re.search(r"^#\s+.+$", md, re.M):
        # 짧은 메모는 front matter만으로 제목을 주기도 한다. 표지가 없으면 본문 제목을 자동 표시한다.
        md = "# " + meta["title"] + "\n\n" + md.lstrip()

    body = (cover_html(meta) if cover else "") + convert(md, accent)
    doc = ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
           '<meta name="doc-cover" content="%d">'
           "<title>%s</title><style>%s</style></head><body>\n%s\n</body></html>\n"
           % (1 if cover else 0, html.escape(title),
              CSS % {"accent": accent, "accent2": accent2}, body))
    open(args[1], "w", encoding="utf-8").write(doc)
    print("HTML 생성:", args[1], "| 제목:", title, "|", len(doc), "바이트",
          "| 표지" if cover else "", "| accent", accent)
    for w in WARNINGS:
        print("경고:", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
