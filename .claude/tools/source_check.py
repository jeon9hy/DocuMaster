"""교차 확인용 원문 대조 — 05 §5의 출처를 열어 값이 원문에 있는지 앞뒤 문장과 함께 보여 준다(cross-check §2).

    python .claude/tools/source_check.py <작업ID> S01=16.5,64.9,659만 S04=58.9 [S07="문장 일부"] [--refresh]
    값은 쉼표로 나눈다(천 단위 쉼표 3,508은 한 값). 값 안에 쉼표가 있으면 `S07=가, 나|다`처럼 `|`로 나눈다

왜 이게 있는가 — 로이드가 WebFetch·curl·PDF 추출을 출처마다 따로 하느라 교차 확인에만 턴 일고여덟 번을 썼다(10-01 실측).
하는 일
  * 05(최신 버전) §5의 `- S01 | 자료명 | 주체 | 날짜 | URL` 행에서 URL(또는 `자료/` 로컬 파일)을 찾는다
  * 원문을 받아 `작업/<ID>/sources/_check/`에 둔다(다시 부르면 받은 것을 쓴다. 새로 받으려면 --refresh)
  * PDF는 쪽마다, HTML은 태그를 걷어 낸 본문에서 값을 찾는다. 숫자는 `16.5`·`1 6 . 5`·`3,508`·`3508`을 같게 본다
  * 찾으면 `쪽 n · «앞뒤 문장»`, 못 찾으면 그렇다고만 적는다
하지 않는 일 — 판정. 찾은 문장의 시점·단위·범위가 05와 같은지는 로이드가 읽고 정한다. 못 찾은 것만 직접 연다.
`환경기록.md` E-056의 막히는 도메인은 받지 않는다 — 02·04의 요르 원문 인용과 대조한다.
종료 코드: 0 전부 찾음 · 1 못 찾은 값이나 못 연 출처가 있다 · 2 입력 오류
"""
from __future__ import annotations

import html as htmllib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-005)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_files import latest, work_root  # noqa: E402

ROOT = work_root()
BASE_05 = "05_verified_research_pack"
BLOCKED = ("pwc.com", "weforum.org", "hbs.edu")  # E-056 — 로이드·유리 쪽에서 403
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
CONTEXT = 70
MAX_BYTES = 40 * 1024 * 1024


def source_rows(text_05: str) -> dict[str, str]:
    """05 §5 → {S01: 행 전체}."""
    m = re.search(r"^## 5\.[^\n]*\n(.*?)(?=^## \d\.|\Z)", text_05, re.S | re.M)
    rows = {}
    for line in (m[1] if m else "").splitlines():
        hit = re.match(r"^\s*-?\s*(S\d{2,3})\s*\|(.*)$", line)
        if hit:
            rows.setdefault(hit[1], hit[2].strip())
    return rows


def locate(row: str) -> tuple[str, str]:
    """출처 행 → ("url", 주소) | ("local", 경로) | ("none", "")."""
    url = re.search(r"https?://[^\s|)>\]]+", row)
    if url:
        return "url", url[0].rstrip(".,")
    local = re.search(r"자료/[^\s|]+", row)
    if local:
        return "local", local[0]
    return "none", ""


def parse_targets(args: list[str]) -> dict[str, list[str]]:
    """`S01=16.5,64.9` → {S01: [16.5, 64.9]}. 천 단위 쉼표(3,508)는 나누지 않는다. 값에 쉼표가 들면 `|`로 구분한다."""
    targets: dict[str, list[str]] = {}
    for arg in args:
        sid, sep, values = arg.partition("=")
        if not sep or not re.fullmatch(r"S\d{2,3}", sid.strip()) or not values.strip():
            raise ValueError(f"`S01=값,값` 형식이 아니다: {arg}")
        quoted = values.strip()
        # 숫자 사이의 `,ddd`만 천 단위 쉼표다(3,508). `41만,659만`·`2041,2055`는 나눈다
        parts = quoted.split("|") if "|" in quoted else re.split(r"(?<!\d),|,(?!\d{3}(?!\d))", quoted)
        targets.setdefault(sid.strip(), []).extend(p.strip() for p in parts if p.strip())
    return targets


def number_pattern(value: str) -> re.Pattern:
    """`16.5` → 숫자 사이 공백·천 단위 쉼표를 허용하고, 더 긴 숫자의 일부는 거른다."""
    core = re.sub(r"[,\s]", "", value)
    pieces = []
    for ch in core:
        if ch.isdigit():
            pieces.append(ch + r"[\s,]?")
        elif ch == ".":
            pieces.append(r"\s?\.\s?")
        else:
            pieces.append(r"\s?" + re.escape(ch))
    body = "".join(pieces)
    body = body[:-len(r"[\s,]?")] if body.endswith(r"[\s,]?") else body
    return re.compile(r"(?<![\d.])" + body + r"(?![\d]|\.\d)")


def text_pattern(value: str) -> re.Pattern:
    words = [re.escape(w) for w in value.split()]
    return re.compile(r"\s*".join(words))


UNIT = {"만": 10_000, "억": 100_000_000}


def pattern_of(value: str) -> re.Pattern:
    if re.fullmatch(r"[\d.,%p\s]+", value) and re.search(r"\d", value):
        return number_pattern(value)
    # `659만`·`1.2억`은 원문이 `6,590,000`처럼 풀어 쓴 경우도 같은 값으로 본다
    unit = re.fullmatch(r"(\d[\d,]*(?:\.\d+)?)\s*([만억])(.*)", value)
    if unit:
        whole = round(float(unit[1].replace(",", "")) * UNIT[unit[2]])
        return re.compile(f"(?:{text_pattern(value).pattern})|(?:{number_pattern(str(whole)).pattern})")
    return text_pattern(value)


def html_text(data: bytes, content_type: str) -> str:
    charset = re.search(r"charset=([\w\-]+)", content_type or "", re.I)
    meta = re.search(rb"<meta[^>]+charset=[\"']?([\w\-]+)", data[:4000], re.I)
    tried = [c for c in (charset[1] if charset else None, meta[1].decode() if meta else None) if c]
    text = None
    for enc in [*tried, "utf-8", "cp949"]:
        try:
            text = data.decode(enc)
            break
        except (LookupError, UnicodeDecodeError):
            continue
    text = text if text is not None else data.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    # 관공서 공지는 본문을 그림으로 올리고 같은 글을 alt에 넣는다(10-01 국민연금공단) — 태그와 함께 버리지 않는다
    text = re.sub(r"(?is)<img\b[^>]*?\balt\s*=\s*([\"'])(.*?)\1[^>]*>", r" \2 ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", htmllib.unescape(text))


def pdf_pages(data: bytes) -> list[str]:
    try:
        import pymupdf as fitz  # 1.24+ 이름 — `fitz`는 사용 중단 경고를 낸다
    except ImportError:
        import fitz
    with fitz.open(stream=data, filetype="pdf") as doc:
        return [re.sub(r"\s+", " ", page.get_text()) for page in doc]


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data, content_type = response.read(MAX_BYTES), response.headers.get("Content-Type", "")
    return follow_shell(url, data, content_type)


def follow_shell(url: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    """본문을 스크립트로 불러오는 껍데기 페이지면 본문 주소를 한 번 더 받는다.

    법제처 `lsInfoP.do?lsiSeq=N`은 조문이 없다 — 같은 페이지의 `efYd`로 `LSW/lsInfoR.do`를 부르면 조문 전문이 온다
    (10-01 E2E: WebFetch·이 도구 모두 lsInfoP에서 조문을 못 읽었다, E-071).
    """
    law = re.match(r"https?://(?:www\.)?law\.go\.kr/(?:LSW/)?lsInfoP\.do\?(?:.*&)?lsiSeq=(\d+)", url)
    effective = re.search(rb"var efYd\s*=\s*'(\d{8})'", data)
    if law and effective:
        return fetch(f"https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq={law[1]}&efYd={effective[1].decode()}")
    return data, content_type


def load(sid: str, kind: str, where: str, cache: Path, refresh: bool) -> list[str]:
    """원문을 쪽 목록으로. HTML·텍스트는 한 쪽."""
    if kind == "local":
        path = ROOT / where
        data, content_type = path.read_bytes(), ""
    else:
        cached = next(iter(sorted(cache.glob(f"{sid}.*"))), None) if not refresh else None
        if cached:
            data, content_type = cached.read_bytes(), "application/pdf" if cached.suffix == ".pdf" else "text/html"
        else:
            data, content_type = fetch(where)
            cache.mkdir(parents=True, exist_ok=True)
            for old in cache.glob(f"{sid}.*"):
                old.unlink()
            is_pdf = data[:5] == b"%PDF-"
            (cache / f"{sid}.{'pdf' if is_pdf else 'html'}").write_bytes(data)
    if data[:5] == b"%PDF-":
        return pdf_pages(data)
    if kind == "local" and not where.lower().endswith((".html", ".htm")):
        return [re.sub(r"\s+", " ", data.decode("utf-8", errors="replace"))]
    return [html_text(data, content_type)]


def context(text: str, start: int, end: int) -> str:
    left = text[max(0, start - CONTEXT):start]
    right = text[end:end + CONTEXT]
    return f"…{left}【{text[start:end]}】{right}…".strip()


def check(job_id: str, targets: dict[str, list[str]], refresh: bool = False) -> int:
    ws = ROOT / "작업" / job_id / "workspace"
    path_05 = latest(ws, BASE_05)
    if path_05 is None:
        print(f"[중단] 05가 없다: 작업/{job_id}/workspace")
        return 2
    rows = source_rows(path_05.read_text(encoding="utf-8"))
    cache = ROOT / "작업" / job_id / "sources" / "_check"
    print(f"# source_check · {job_id} · {path_05.name}")
    missing = 0
    for sid, values in targets.items():
        row = rows.get(sid)
        print(f"\n## {sid} · {(row or '05 §5에 행 없음')[:90]}")
        if row is None:
            missing += len(values)
            continue
        kind, where = locate(row)
        if kind == "none":
            print("  열 곳 없음 — URL·로컬 경로가 없다. 직접 확인한다")
            missing += len(values)
            continue
        if kind == "url" and any(re.search(rf"(^|\.){re.escape(d)}$", re.sub(r"^https?://([^/:]+).*", r"\1", where))
                                 for d in BLOCKED):
            print("  열지 않음(E-056 막히는 도메인) — 02·04의 요르 원문 인용(쪽 포함)과 대조한다")
            missing += len(values)
            continue
        try:
            pages = load(sid, kind, where, cache, refresh)
        except (OSError, urllib.error.URLError, ValueError, RuntimeError) as error:
            print(f"  못 열었다: {type(error).__name__} {str(error)[:80]} — 직접 연다")
            missing += len(values)
            continue
        size = sum(len(p) for p in pages)
        if size < 200:
            print(f"  본문이 거의 없다({size}자) — 스크립트로 그리는 페이지일 수 있다. 직접 연다")
        misses = 0
        for value in values:
            pattern = pattern_of(value)
            hits = [(n, m) for n, page in enumerate(pages, 1) for m in pattern.finditer(page)]
            if not hits:
                print(f"  ✗ {value} — 원문에서 못 찾았다")
                missing += 1
                misses += 1
                continue
            more = f" (외 {len(hits) - 1}곳)" if len(hits) > 1 else ""
            for n, m in hits[:2]:
                where_hit = f"쪽 {n}" if len(pages) > 1 else "본문"
                print(f"  ✓ {value} · {where_hit}{more if (n, m) == hits[0] else ''} · {context(pages[n - 1], m.start(), m.end())}")
        if misses and size >= 200:
            print(f"  (받은 원문 {len(pages)}쪽 · {size:,}자 — 본문을 스크립트로 그리는 페이지면 값이 없을 수 있다)")
    print(f"\n결과: 못 찾음·못 엶 {missing}건 — " + ("찾은 문장의 시점·단위·범위를 05와 대조한다" if not missing
                                              else "✗·못 연 것만 직접 연다(검색 스니펫은 확인이 아니다)"))
    return 1 if missing else 0


def main() -> int:
    args = sys.argv[1:]
    refresh = "--refresh" in args
    args = [a for a in args if a != "--refresh"]
    if len(args) < 2:
        print(__doc__)
        return 2
    try:
        targets = parse_targets(args[1:])
    except ValueError as error:
        print(f"[중단] {error}")
        return 2
    return check(args[0], targets, refresh)


if __name__ == "__main__":
    sys.exit(main())
