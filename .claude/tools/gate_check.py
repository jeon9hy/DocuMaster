"""05 / PPT 06·07 / DOC 07 게이트 — 사실 재유입과 형식 위반을 사람이 읽기 전에 걸러 낸다.

사용:
    python .claude/tools/gate_check.py <작업ID> 05|06|07 [--file <대상 경로>]

05는 아냐가 읽는 §2·§5만 잰다 — §2의 금지·미확인·절 참조는 원고의 해명 문장이 된다(E-060).

대상은 workspace에서 가장 높은 버전(_v02, _v03 …)을 자동으로 고른다. 모드는 대상 헤더에서 읽는다.
판정:
  FAIL  확정 위반 — 담당에게 돌려보낸다. 하나라도 있으면 종료 코드 1
  CHECK 사람이 닫을 것 — 전부 보고 `기록.md`에 닫은 이유를 한 줄씩 남긴다
이 검사는 읽기를 대신하지 않는다. 표현만 바꾼 REMOVE와 강도 과장은 못 잡는다(E-021).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-005·E-024)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
BASES = {
    "00": "00_user_brief", "05": "05_verified_research_pack", "06": "06_detailed_plan",
    "pack": "07_notebooklm_presentation_pack", "07_doc": "07_final_document",
}
# 형식 이름(E-026) · 판단을 넘기는 말(세부기획 §3) · 강도 후보(E-021) · DOC 본문에 들어온 검수의 말(E-057)
TRACE_WORDS = re.compile(
    r"이 (보고서|지침서|가이드|문서|글)(는|은|에서|가|의)|것이 안전하다|"
    r"근거이지|근거일 뿐|까지만 말|다른 주장이다|가장 정직한|한 줄로 (요약|정리)|유의해야")
# 독자가 하지 않은 오해를 막는 해명 문장(E-057·E-060) — 한계를 모은 `::: note` 한 곳 밖이면 FAIL
HEDGE_WORDS = re.compile(
    r"(단정|말|판단|비교|평균|해석|특정|추정|일반화|확대|결론)(할|하기|해|내기|짓기)? ?수(는|도|가)? ?없|"
    r"(단정하|판단하|보|말하|결론짓|평가하)기(는|가|도)? (어렵|이르)|"
    r"(읽어|해석해|봐|보아|써|받아들여)서는 안|로 (읽어야|읽는다|읽을)|읽는 것이|(다르게|달리) 읽힌|읽으면 안|"
    r"인과(관계|분석|적)?(은|는|가|이|로)? (아니|볼 수)|(뜻|의미|말)(은|이) 아니|"
    r"(설명|추정|특정|언급|확인)하지 (않았|못)|(특정|확인)되지 않|찾지 못|찾을 수 없|확보하지 못|"
    r"담기지 않|다루지 (못|않)|근거는? 없")
# 장마다 같은 틀로 닫는 관전 권유 — 3회 이상이면 CHECK
WATCH_WORDS = re.compile(r"보는 것이 (좋|필요)|지켜볼|주시할|볼 (대목|지점)|눈여겨")
# 05 §2(아냐가 읽는 사실)에 들어가면 안 되는 것 — 집필 금지·미확인 꼬리·절/파일 참조·에이전트 이름
DIRECTIVE_WORDS = re.compile(
    r"쓰지 않|쓸 수 없|쓰지 말|묶지 않|내지 않는다|금지|불가(?!피)|미확인|확인되지 않|추정되지 않|열리지 않|"
    r"위 CAUTION|§\s?\d|(?<![\d.\-])0[1-4](?![\d.%\-]) ?(§|을|를|와|과|의|에)|요르|로이드|아냐|"
    r"유리(가|는|의|에게)? ?(확인|질의|판정|직접)")
FORMAT_WORDS = re.compile(r"차트|그래프|카드|타임라인|인포그래픽|막대|도넛|파이 ?그래프|아이콘|레이아웃|(?:^|(?<=\s))표(?=[로를에는가와]|\s|$)")
VAGUE_WORDS = re.compile(r"적절히|적당히|알아서|필요시|필요하면|등등|재량껏")
STRONG_WORDS = re.compile(r"때문이다|때문에|덕분|결정적|입증|증명|반드시|확실히|분명히|모든 |누구나|최고의|압도적")
LAYOUT = re.compile(r"\b[xy]\s*=|\d\s*(px|pt)\b|너비|화면의 (약 )?\d|영역")  # 좌표·크기 줄은 수치 검사에서 뺀다
# 덱 유형별 (제목, 화면 문구) 한 줄 한도(공백 제외) — 공통/발표_<유형>.md §3과 같게 유지
DECK_CAPS = {"스토리": (10, 16), "학술": (24, 40), "브리핑": (24, 40)}


def deck_line(kind: str) -> str:
    """유형 파일 §8의 제작 지시 줄 — 코드에 박지 않고 파일에서 읽는다."""
    f = ROOT / ".claude" / "공통" / f"발표_{kind}.md"
    m = re.search(r"^## 8\..*?^`(.+?)`", f.read_text(encoding="utf-8"), re.S | re.M) if f.exists() else None
    return norm(m[1]) if m else ""
SKIP_SECTIONS = re.compile(r"Art Direction|Deck Rhythm|제작 지시|자산|헤더|Sources|출처$|근거 목록|근거표")

results: list[tuple[str, str, str]] = []


def report(level: str, name: str, msg: str) -> None:
    results.append((level, name, msg))


def latest(ws: Path, base: str) -> Path | None:
    cands = [p for p in ws.glob(base + "*.md") if re.fullmatch(re.escape(base) + r"(_v\d+)?\.md", p.name)]
    if not cands:
        return None
    return max(cands, key=lambda p: int((re.search(r"_v(\d+)\.md$", p.name) or [0, 1])[1]))


def norm(s: str) -> str:
    s = re.sub(r"\*\*|[\"“”「」『』]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def section_table(text: str, title: str) -> list[list[str]]:
    """`### <title>` 아래 첫 표의 데이터 행(셀 목록)."""
    m = re.search(rf"^#+\s*{title}\b.*?$(.*?)(?=^#+\s|\Z)", text, re.S | re.M)
    if not m:
        return []
    rows = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
    if len(rows) < 3:
        return []
    header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    out = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows[2:]]
    return [header] + out


def declared_count(t05: str, label: str) -> int | None:
    """05 헤더의 `REMOVE 0`·`CAUTION 0`처럼 명시된 판정 개수."""
    header = t05.split("--- 헤더 끝 ---", 1)[0]
    match = re.search(rf"\b{label}\s*(\d+)\b", header, re.I)
    return int(match[1]) if match else None


def remove_items(t05: str) -> list[tuple[str, list[str]]]:
    tab = section_table(t05, "REMOVE")
    return [(r[0], re.findall(r"\bS\d{2,3}\b", r[0])) for r in tab[1:] if r and r[0]]


def caution_items(t05: str) -> list[tuple[str, str]]:
    tab = section_table(t05, "CAUTION")
    if not tab:
        return []
    header = tab[0]
    col = next((i for i, h in enumerate(header) if "문구" in h or "문장" in h), len(header) - 1)
    return [(r[0], norm(r[col])) for r in tab[1:] if len(r) > col and r[col]]


def numbers(text: str, skip_layout: bool) -> dict[str, str]:
    """본문 수치 → 처음 나온 줄. 한 자리 수(%가 없는)는 제외한다."""
    out: dict[str, str] = {}
    section, sub = "", ""
    for line in text.splitlines():
        h = re.match(r"^(#+)\s*(.*)", line)
        if h:
            if len(h[1]) <= 2:
                section, sub = h[2], ""
            else:
                sub = h[2]
            continue
        if SKIP_SECTIONS.search(section) or SKIP_SECTIONS.search(sub):
            continue
        if LAYOUT.search(line):
            continue
        body = re.sub(r"^\s*(\d+[.)]|[-*])\s+", "", line)
        body = re.sub(r"Slide\s*\d+|#[0-9A-Fa-f]{6}\b|https?://\S+|§\s*\d+", " ", body)
        for m in re.finditer(r"(?<![A-Za-z0-9.,\-_])(\d[\d,]*(?:\.\d+)?)(%p|%)?", body):
            val, unit = m.group(1).replace(",", "").rstrip("."), m.group(2) or ""
            if skip_layout and unit == "%" and sub.startswith("화면"):
                continue
            if len(val) == 1 and not unit:
                continue
            out.setdefault(val + unit, line.strip()[:90])
    return out


def base_numbers(*texts: str) -> set[str]:
    s: set[str] = set()
    for t in texts:
        for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)(%p|%)?", t):
            v = m.group(1).replace(",", "").rstrip(".")
            s.update({v, v + (m.group(2) or "")})
    return s


def check_numbers(target: str, allowed: set[str], skip_layout: bool) -> None:
    extra = {k: v for k, v in numbers(target, skip_layout).items() if k not in allowed}
    if not extra:
        report("OK", "수치", "05·06에 없는 수치 없음 (한 자리 수 제외)")
    for k, line in extra.items():
        report("CHECK", "수치", f"05에 없는 {k} — {line}")


def check_remove(target: str, t05: str) -> None:
    items = remove_items(t05)
    if not items:
        if declared_count(t05, "REMOVE") == 0:
            report("OK", "REMOVE", "05 헤더에 REMOVE 0건으로 명시")
        else:
            report("CHECK", "REMOVE", "05에서 REMOVE 표를 못 읽었다 — 05 §1 형식 확인")
        return
    hit = False
    for label, ids in items:
        for i in ids:
            for line in target.splitlines():
                if not re.search(rf"\b{i}\b", line):
                    continue
                hit = True
                handled = re.search(r"REMOVE|않는다|않았다|넣지|쓰지|만들지|금지|삭제", line)
                report("CHECK" if handled else "FAIL", "REMOVE",
                       f"{i} — " + ("처리 언급으로 보인다: " if handled else "다시 나온다: ") + line.strip()[:70])
    if not hit:
        report("OK", "REMOVE", f"REMOVE {len(items)}건의 근거 ID 재등장 없음")
    report("CHECK", "REMOVE", "표현만 바꾼 부활은 읽어서 본다: " + " / ".join(l[:30] for l, _ in items))


def check_caution(target: str, t05: str, strict: bool) -> None:
    items = caution_items(t05)
    if not items:
        if declared_count(t05, "CAUTION") == 0:
            report("OK", "CAUTION", "05 헤더에 CAUTION 0건으로 명시")
        else:
            report("CHECK", "CAUTION", "05에서 CAUTION 표를 못 읽었다 — 05 §1 형식 확인")
        return
    body = norm(target)
    missing = [(l, s) for l, s in items if s not in body]
    if strict:
        for l, _ in missing:
            report("FAIL", "CAUTION", f"문구가 그대로 없다 — {l[:40]}")
    elif missing:
        report("CHECK", "CAUTION", "글자 그대로가 아니다 — 한정·발표자 메모로 뜻이 살아 있는지 본다: "
               + " / ".join(l[:25] for l, _ in missing))
    if not missing:
        report("OK", "CAUTION", f"{len(items)}건 전부 글자 그대로 있다")


def check_state_bookkeeping(state: str) -> None:
    """완료 게이트 전에 실제 호출 ID 대신 자리표시자가 남았는지 검사한다."""
    line = next((line for line in state.splitlines() if line.startswith("## 세션")), "")
    if not line:
        report("FAIL", "상태 기록", "상태.md에 `## 세션` 줄이 없다 — 로이드가 기록")
        return
    placeholders = re.findall(r"실행 후 기록|\(미실행\)", line)
    if placeholders:
        report("FAIL", "상태 기록", "실제 ID 또는 `해당 없음(이유)`으로 바꾸지 않은 자리표시자: "
               + ", ".join(dict.fromkeys(placeholders)))
    else:
        report("OK", "상태 기록", "세션·에이전트 자리표시자 없음")


def check_doc_sources(target: str) -> None:
    """본문·비주얼 citation과 sources 블록의 양방향 무결성을 검사한다."""
    match = re.search(r"^:::\s*sources\b[^\n]*\n(.*?)^:::\s*$", target, re.S | re.M)
    if not match:
        report("FAIL", "출처", "`::: sources` 블록이 없다")
        return
    body = target[:match.start()]
    cited = set(re.findall(r"\[S(\d{2,3})\]", body))
    rows = re.findall(r"^\s*S(\d{2,3})\s*\|", match.group(1), re.M)
    listed = set(rows)
    duplicate = sorted({sid for sid in rows if rows.count(sid) > 1})
    missing = sorted(cited - listed)
    unused = sorted(listed - cited)
    if duplicate:
        report("FAIL", "출처", "출처 ID 중복: " + ", ".join("S" + sid for sid in duplicate))
    if missing:
        report("FAIL", "출처", "citation에 대응하는 출처 없음: " + ", ".join("S" + sid for sid in missing))
    if unused:
        report("FAIL", "출처", "최종 문서에서 쓰지 않은 출처 행: " + ", ".join("S" + sid for sid in unused))
    if not cited:
        report("CHECK", "출처", "본문·비주얼에 `[Snn]` citation이 없다")
    elif not duplicate and not missing and not unused:
        report("OK", "출처", f"citation {len(cited)}건과 출처 행이 양방향 대응")
    lines = [l for l in match.group(1).splitlines() if re.match(r"\s*S\d{2,3}\s*\|", l)]
    no_link = [l.split("|")[0].strip() for l in lines if not re.search(r"https?://|p\.\s*\d|쪽|시트", l)]
    unknown = [l.split("|")[0].strip() for l in lines if re.search(r"\|\s*미상\s*\|", l)]
    if no_link:
        report("CHECK", "출처", f"링크·위치 없는 출처 {len(no_link)}건 — 05 §5에 URL이 있는지 본다: " + ", ".join(no_link[:12]))
    if unknown:
        report("CHECK", "출처", f"날짜 미상 {len(unknown)}건: " + ", ".join(unknown[:12]))


def check_hedges(target: str) -> None:
    """해명 문장은 한계를 모은 `::: note` 한 곳에만 둔다(문서규격 §2)."""
    body = re.split(r"^:::\s*sources\b", target, maxsplit=1, flags=re.M)[0]
    out, notes, in_note, note_no = [], set(), False, 0
    for i, line in enumerate(body.splitlines(), 1):
        if re.match(r"^:::\s*note\b", line):
            in_note, note_no = True, note_no + 1
            continue
        if in_note and re.match(r"^:::\s*$", line):
            in_note = False
            continue
        if re.match(r"^\s*(title|subtitle):", line):
            continue
        m = HEDGE_WORDS.search(line)
        if m and in_note:
            notes.add(note_no)
        elif m:
            out.append(f"{i}행 「{m.group(0)}」 {line.strip()[:60]}")
    for h in out[:15]:
        report("FAIL", "해명 문장", h + " — 문장을 지우거나 조건을 라벨로")
    if len(out) > 15:
        report("FAIL", "해명 문장", f"… 외 {len(out) - 15}건")
    if len(notes) > 1:
        report("FAIL", "해명 문장", f"한계가 note {len(notes)}곳에 흩어져 있다 — 한 곳으로")
    if not out and len(notes) <= 1:
        report("OK", "해명 문장", "note 밖 해명 문장 없음")
    watch = WATCH_WORDS.findall(body)
    if len(watch) >= 3:
        report("CHECK", "관전 권유", f"`지켜보라`류 {len(watch)}회 — 시사점이 해석 없이 관전 권유로 끝나지 않는지(문서규격 §1)")


def check_05(t05: str) -> None:
    """아냐가 읽는 05 §2·§5가 원고에 그대로 옮겨도 되는 긍정문인지 잰다."""
    sec = lambda n: (re.search(rf"^## {n}\.[^\n]*\n(.*?)(?=^## \d\.|\Z)", t05, re.S | re.M) or [None, ""])[1]
    s2, s5 = sec(2), sec(5)
    if not s2.strip():
        report("FAIL", "05 §2", "`## 2.` 절이 없다")
    hits = []
    for i, line in enumerate(s2.splitlines(), 1):
        m = DIRECTIVE_WORDS.search(line)
        if m:
            hits.append(f"§2 {i}행 「{m.group(0)}」 {line.strip()[:60]}")
    for h in hits[:15]:
        report("FAIL", "05 §2", h + " — 긍정문으로 바꾸거나 §4로")
    if len(hits) > 15:
        report("FAIL", "05 §2", f"… 외 {len(hits) - 15}건")
    if s2.strip() and not hits:
        report("OK", "05 §2", "금지·미확인·참조 없음")
    ids = sorted(set(re.findall(r"S(\d{2,3})", s2)))
    rows = {m[0]: m[1] for m in re.findall(r"^\s*-?\s*S(\d{2,3})\s*\|(.*)$", s5, re.M)}
    missing = [f"S{i}" for i in ids if i not in rows]
    no_link = [f"S{i}" for i, r in rows.items() if not re.search(r"https?://|자료/|p\.\s*\d|쪽", r)]
    if re.search(r"02|04", s5) and re.search(r"따른다|참조|참고", s5):
        report("FAIL", "05 §5", "02·04를 가리킨다 — 05는 혼자 읽혀야 한다")
    if missing:
        report("FAIL", "05 §5", "§2 근거 ID의 출처 행 없음(`- S01 | 자료명 | 주체 | 날짜 | URL`): " + ", ".join(missing[:15]))
    if no_link:
        report("FAIL", "05 §5", "URL·위치 없는 출처 행: " + ", ".join(no_link[:15]))
    if ids and not missing and not no_link:
        report("OK", "05 §5", f"§2 근거 {len(ids)}건 모두 출처 행·URL 있음")


def slides(text: str) -> list[tuple[int, str]]:
    parts = re.split(r"^## Slide\s+(\d+)[^\n]*$", text, flags=re.M)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def field(block: str, name: str) -> str:
    m = re.search(rf"^###\s*{name}\s*$(.*?)(?=^###\s|\Z)", block, re.S | re.M)
    return m.group(1).strip() if m else ""


def kind_of(text: str) -> str:
    """00·06·07에 적힌 덱 유형. 없으면 빈 문자열."""
    m = re.search(r"^- 덱 유형[^:\n]*:\s*(스토리|학술|브리핑)", text, re.M)
    return m[1] if m else ""


def check_kinds(kinds: dict[str, str]) -> None:
    """00 → 06 → 07의 덱 유형이 모두 있고 같아야 한다(유형 drift 차단, E-048)."""
    missing = [k for k, v in kinds.items() if not v]
    for k in missing:
        report("FAIL", "유형", f"{k}에 덱 유형이 없다 — 기본값으로 추정하지 않는다")
    found = {v for v in kinds.values() if v}
    if len(found) > 1:
        report("FAIL", "유형", "덱 유형 불일치 — " + " · ".join(f"{k} {v or '없음'}" for k, v in kinds.items()))
    elif found and not missing:
        report("OK", "유형", f"{' → '.join(kinds)} 모두 {found.pop()}")


# 유형별 흐름 단계 — 장 이름(## Slide n — …)에서 찾는다. 갈래가 여럿이면 가장 잘 맞는 갈래로 잰다.
# 이름이 달라도 있을 수 있으니 CHECK (발표_<유형>.md §1)
FLOW_STEPS = {
    "학술": {
        "연구": [("질문|문제", "연구 질문"), ("방법|자료", "자료·방법"), ("결과", "결과"), ("논의|해석", "논의"), ("결론", "결론"), ("참고문헌", "참고문헌")],
        "리뷰·이론": [("질문", "핵심 질문"), ("개념|배경", "개념·배경"), ("연구|근거|문헌", "주요 연구·근거"), ("비교|쟁점", "비교·쟁점"),
                    ("종합|해석|논의", "종합·해석"), ("결론", "결론"), ("참고문헌", "참고문헌")],
    },
    "브리핑": {
        "의사결정 보고": [("결론|요약", "핵심 결론·요청 요약"), ("현황", "현황"), ("원인", "원인"), ("선택지|위험", "선택지·위험"), ("제안|다음 단계|요청", "제안·다음 단계"), ("출처|한계", "출처·한계")],
        "설명·교육": [("왜 중요|중요", "왜 중요한가"), ("현황", "현황"), ("결론|할 일", "결론·할 일"), ("출처|한계", "출처·한계")],
    },
    "스토리": {},
}


def check_pack(pack: str, t06: str, t00: str = "") -> None:
    ps, s06 = slides(pack), slides(t06)
    n_head = re.search(r"슬라이드 수:\s*(\d+)", pack)
    nums = [n for n, _ in ps]
    if n_head and int(n_head[1]) == len(ps) == len(s06) and nums == list(range(1, len(ps) + 1)):
        report("OK", "LOCKED", f"슬라이드 {len(ps)}장 — 헤더·06과 같다")
    else:
        report("FAIL", "LOCKED", f"슬라이드 수 불일치 — 헤더 {n_head[1] if n_head else '없음'} · 팩 {len(ps)} · 06 {len(s06)}")
    if "# 제작 지시" not in pack:
        report("FAIL", "형식", "`# 제작 지시`가 없다 — 도구가 프롬프트를 못 만든다")

    # 덱 유형 (공통/발표_<유형>.md) — 줄 한도와 제작 지시 유형 줄
    kinds = {"00": kind_of(t00), "06": kind_of(t06), "07": kind_of(pack)}
    check_kinds(kinds)
    kind = kinds["07"] or kinds["06"] or kinds["00"]
    if not kind:
        return  # 유형을 모르면 유형 규칙으로 잴 수 없다 — 위에서 FAIL
    caps = DECK_CAPS[kind]
    if not deck_line(kind) or deck_line(kind) not in norm(pack.split("# 제작 지시", 1)[-1]):
        report("FAIL", "유형", f"`# 제작 지시`에 발표_{kind}.md §8 줄이 글자 그대로 없다")
    head_art = pack.split("## Slide", 1)[0]
    if kind in ("학술", "브리핑"):
        for n, b in ps:
            if field(b, "제목") in ("", "없음") and n > 1:
                report("FAIL", "유형", f"Slide {n}: {kind} 덱은 모든 본문 장에 주장형 제목을 둔다")
        style = re.search(r"^- 화풍:\s*(.+)$", head_art, re.M)
        if style and not re.match(r"(그림 )?없음", style[1].strip()):
            report("CHECK", "유형", f"{kind} 덱에 화풍이 있다 — 연구·보고 대상 자체의 그림인지 확인")
        cm = re.search(r"^- Character Model:\s*(.*)$", head_art, re.M)
        if cm and cm[1].strip() and not cm[1].strip().startswith("없음"):
            report("CHECK", "유형", f"{kind} 덱에 Character Model이 있다 — 장식이 아니라 대상 자체의 그림인지 확인")
    names = " ".join(re.findall(r"^## Slide\s+\d+\s*[—-]\s*(.+)$", pack, re.M))
    branches = FLOW_STEPS[kind]
    if branches:
        sub = re.search(r"^- 덱 유형[^:\n]*:\s*\S+\s*\(([^)]+)\)", pack, re.M)
        pool = {sub[1]: branches[sub[1]]} if sub and sub[1] in branches else branches
        lost_by = {b: [label for pat, label in steps if not re.search(pat, names)] for b, steps in pool.items()}
        best = min(lost_by, key=lambda b: len(lost_by[b]))
        if lost_by[best]:
            report("CHECK", "흐름", f"{kind}({best}) 흐름 단계로 보이는 장이 없다: {', '.join(lost_by[best])} — 장 이름이 달라도 읽어서 확인")
        else:
            report("OK", "흐름", f"{kind}({best}) 흐름 단계가 모두 있다")

    # 출처 표시: 아니오 인 장에 출처가 있으면 안 된다
    src_no = {n for n, b in s06 if re.search(r"출처 표시:\s*아니오", b)}
    src_yes = {n for n, b in s06 if re.search(r"출처 표시:\s*예", b)}
    for n, b in ps:
        src = field(b, "출처")
        if n in src_no and src and src != "없음":
            report("FAIL", "출처", f"Slide {n}: 06은 「출처 표시: 아니오」인데 출처가 있다")
        if n in src_yes and src in ("", "없음"):
            report("FAIL", "출처", f"Slide {n}: 06은 「출처 표시: 예」인데 07에 출처가 없다")
        if re.search(r"\[S\d+\]|https?://", field(b, "제목") + field(b, "화면 문구") + src):
            report("FAIL", "출처", f"Slide {n}: 화면 필드에 근거 ID나 URL이 있다")
        title = {norm(x.lstrip("- ")) for x in field(b, "제목").splitlines() if x.strip()}
        lines = {norm(x.lstrip("- ")) for x in field(b, "화면 문구").splitlines() if x.strip()}
        if (title & lines) - {"없음"}:
            report("FAIL", "문구", f"Slide {n}: 제목과 화면 문구에 같은 줄이 있다")
        # 한 줄 길이 — 공백 빼고, 덱 유형별 한도 (발표_<유형>.md §3, E-042)
        for key, cap in zip(("제목", "화면 문구"), caps):
            for x in field(b, key).splitlines():
                x = x.strip().lstrip("- ").strip()
                if x != "없음" and len(re.sub(r"\s", "", x)) > cap:
                    report("FAIL", "줄 길이", f"Slide {n}: {key} {cap}자 초과 — {x}")
        # 수치가 화면에 있는데 출처가 없다 (발표규격 §4)
        if re.search(r"\d[\d,.]*\s*(%|표|명|위|배)", field(b, "화면 문구")) and src in ("", "없음"):
            report("FAIL", "출처", f"Slide {n}: 화면에 수치가 있는데 출처가 없다")

    # Character Model — 모든 장에 글자 그대로 (E-036)
    cm = re.search(r"^- Character Model:(.*?)(?=^- \S|^## |\Z)", pack, re.S | re.M)
    models: dict[str, str] = {}
    if cm:
        for raw in [cm.group(1)] + cm.group(1).splitlines():
            raw = raw.strip().lstrip("- ").strip()
            parts = [p.strip() for p in raw.split(" · ")]
            if len(parts) >= 2 and not raw.startswith("없음"):
                models[parts[0]] = norm(" · ".join(p for p in parts[1:] if not p.startswith(("외형 근거", "틀리기 쉬운"))))
    bad = 0
    for n, b in ps:
        for line in re.findall(r"^- 캐릭터:\s*(.+)$", field(b, "화면"), re.M):
            if line.strip().startswith("없음"):
                continue
            name = re.split(r"\s*[—-]\s*", line, 1)[0].strip()
            if name in models and norm(line) != models[name]:
                bad += 1
                report("FAIL", "Character", f"Slide {n}: {name}의 문장이 Character Model과 다르다")
            elif name not in models:
                bad += 1
                report("FAIL", "Character", f"Slide {n}: {name}가 Character Model에 없다")
    if models and not bad:
        report("OK", "Character", f"{len(models)}명 — 등장하는 모든 장에서 글자 그대로")

    # 화풍 — 스토리 덱은 그림이 나오는 장마다 Art Direction 화풍 문장을 그대로 (E-046)
    style = re.search(r"^- 화풍:\s*(.+)$", pack.split("## Slide", 1)[0], re.M)
    if kind == "스토리" and style:
        want, miss = norm(style[1]), []
        for n, b in ps:
            has_char = any(not l.strip().startswith("없음") for l in re.findall(r"^- 캐릭터:\s*(.+)$", field(b, "화면"), re.M))
            got = re.search(r"^- 화풍:\s*(.+)$", field(b, "화면"), re.M)
            if (has_char or got) and (not got or norm(got[1]) != want):
                miss.append(str(n))
        if miss:
            report("FAIL", "화풍", "Art Direction 화풍 문장이 그대로가 아닌 장: " + ", ".join(miss))
        else:
            report("OK", "화풍", "그림이 나오는 모든 장에서 글자 그대로")


def check_words(target: str, pat: re.Pattern, level: str, name: str, why: str, skip: str = "") -> None:
    hits = []
    for i, line in enumerate(target.splitlines(), 1):
        if skip and re.search(skip, line):
            continue
        m = pat.search(line)
        if m:
            hits.append(f"{i}행 「{m.group(0)}」 {line.strip()[:60]}")
    for h in hits[:15]:
        report(level, name, h)
    if len(hits) > 15:
        report(level, name, f"… 외 {len(hits) - 15}건")
    if not hits:
        report("OK", name, f"{why} 없음")


def main() -> int:
    args = sys.argv[1:]
    file_arg = None
    if "--file" in args:
        i = args.index("--file")
        file_arg = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2 or args[1].lower() not in {"05", "06", "07"}:
        print(__doc__)
        return 2
    job, stage = args[0], args[1].lower()
    ws = ROOT / "작업" / job / "workspace"
    f = {k: latest(ws, v) for k, v in BASES.items()}
    if not f["00"] or not f["05"]:
        print(f"[중단] 00·05가 없다: {ws}")
        return 2
    read = lambda p: p.read_text(encoding="utf-8") if p else ""
    t00, t05, t06 = read(f["00"]), read(f["05"]), read(f["06"])
    mode_match = re.search(r"모드\s*:\s*(DOCUMENT|PRESENTATION)", t00.split("--- 헤더 끝 ---")[0])
    ppt = mode_match[1] == "PRESENTATION" if mode_match else bool(slides(t06))
    if stage == "05":
        p05 = (Path(file_arg) if Path(file_arg).is_absolute() else ROOT / file_arg) if file_arg else f["05"]
        print(f"# gate_check · {job} · 05 · 아냐가 읽는 §2·§5\n대상 {p05.name}\n")
        check_05(read(p05))
        return summarize()

    if stage == "06":
        if not ppt:
            print("[중단] DOCUMENT는 06 단계가 없다 — 00·05에서 아냐 07로 간다")
            return 2
        target_path = f["06"]
    elif ppt:
        target_path = f["pack"]
    else:
        target_path = f["07_doc"]
    if file_arg:
        target_path = Path(file_arg) if Path(file_arg).is_absolute() else ROOT / file_arg
    if not target_path or not target_path.exists():
        print(f"[중단] 대상 파일이 없다 ({stage})")
        return 2
    target = read(target_path)
    # 대상의 기획 개정(r1·r2…)과 같은 개정의 00·06을 기준으로 쓴다 — 한 작업에 개정이 공존해도 섞이지 않게.
    # 개정 표시가 없는 파일은 r1로 본다.
    rev_of = lambda text: (re.search(r"(?<![A-Za-z])r(\d+)(?!\d)", text.split("--- 헤더 끝 ---")[0]) or [0, "1"])[1]
    rev = rev_of(target) if "--- 헤더 끝 ---" in target else None
    for key in (("00", "05", "06") if ppt else ("00", "05")) if rev else ():
        cands = [p for p in ws.glob(BASES[key] + "*.md") if re.fullmatch(re.escape(BASES[key]) + r"(_v\d+)?\.md", p.name)]
        same = [p for p in cands if rev_of(read(p)) == rev]
        if same:
            f[key] = max(same, key=lambda p: int((re.search(r"_v(\d+)\.md$", p.name) or [0, 1])[1]))
    t00, t05, t06 = read(f["00"]), read(f["05"]), read(f["06"])
    mode = "PRESENTATION" if ppt else "DOCUMENT"
    structure = f["06"].name if ppt and f["06"] else "아냐 직접 설계"
    revision = "r" + rev if rev else "개정 표시 없음(최신본)"
    print(f"# gate_check · {job} · {stage} · {mode} · {revision}\n대상 {target_path.name} · 근거 {f['05'].name} · 구조 {structure} · 브리프 {f['00'].name}\n")

    allowed = base_numbers(t00, t05, t06) if ppt and stage == "07" else base_numbers(t00, t05)
    check_numbers(target, allowed, skip_layout=ppt)
    check_remove(target, t05)

    if stage == "06":
        check_caution(target, t05, strict=not ppt)
        check_words(target, FORMAT_WORDS, "CHECK", "형식 이름", "형식 이름(E-026)", skip=r"^#|금지선|피할")
        check_words(target, VAGUE_WORDS, "CHECK", "판단 위임", "판단을 넘기는 말")
        if ppt:
            check_kinds({"00": kind_of(t00), "06": kind_of(target)})
    elif ppt:
        check_pack(target, t06, t00)
        check_caution(target, t05, strict=False)
        screen = "\n".join(field(b, k) for _, b in slides(target) for k in ("제목", "화면 문구", "한정"))
        check_words(screen, STRONG_WORDS, "CHECK", "강도", "화면 문구의 강도 후보")
    else:
        check_doc_sources(target)
        check_caution(target, t05, strict=False)
        check_words(target, STRONG_WORDS, "CHECK", "강도", "강도 후보", skip=r"^(title|subtitle|kind|date|org|accent)")
        body = re.split(r"^:::\s*sources\b", target, maxsplit=1, flags=re.M)[0]
        check_words(body, TRACE_WORDS, "CHECK", "검수 흔적", "본문에 들어온 검수의 말")
        check_hedges(target)
        check_words(body, re.compile(r"\S\s*[—–]\s*\S"), "CHECK", "대시", "본문 문장의 대시(문서규격 §2)",
                    skip=r"^\s*(#|title:|subtitle:|source:)|\|")
    if stage == "07":
        check_state_bookkeeping(read(ws.parent / "상태.md"))

    return summarize()


def summarize() -> int:
    order = {"FAIL": 0, "CHECK": 1, "OK": 2}
    for level, name, msg in sorted(results, key=lambda r: order[r[0]]):
        print(f"{level:5} [{name}] {msg}")
    n_fail = sum(r[0] == "FAIL" for r in results)
    n_check = sum(r[0] == "CHECK" for r in results)
    print(f"\n결과: FAIL {n_fail} · CHECK {n_check} — "
          + ("담당에게 돌려보낸다" if n_fail else "CHECK를 닫고 기록하면 통과" if n_check else "통과"))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
