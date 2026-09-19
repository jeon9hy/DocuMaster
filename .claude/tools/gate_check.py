"""06·06B·07 게이트의 기계 검사 — 사실 재유입과 LOCKED 위반을 사람이 읽기 전에 걸러 낸다.

사용:
    python .claude/tools/gate_check.py <작업ID> 06|06b|07 [--file <대상 경로>]

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
    "06b_doc": "06_visual_direction", "pack": "07_notebooklm_presentation_pack", "07_doc": "07_final_document",
}
# 형식 이름(E-026) · 판단을 넘기는 말(세부기획 §4) · 강도 후보(E-021)
FORMAT_WORDS = re.compile(r"차트|그래프|카드|타임라인|인포그래픽|막대|도넛|파이 ?그래프|아이콘|레이아웃|(?:^|(?<=\s))표(?=[로를에는가와]|\s|$)")
VAGUE_WORDS = re.compile(r"적절히|적당히|알아서|필요시|필요하면|등등|재량껏")
STRONG_WORDS = re.compile(r"때문이다|때문에|덕분|결정적|입증|증명|반드시|확실히|분명히|모든 |누구나|최고의|압도적")
LAYOUT = re.compile(r"\b[xy]\s*=|\d\s*(px|pt)\b|너비|화면의 (약 )?\d|영역")  # 좌표·크기 줄은 수치 검사에서 뺀다
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


def heads(text: str, pat: str) -> list[str]:
    return [norm(m) for m in re.findall(pat, text, re.M)]


def check_doc_structure(t06: str, target: str, pat_target: str, what: str) -> None:
    sec = re.search(r"^## 장별 지시(.*?)(?=^## (?!#)|\Z)", t06, re.S | re.M)
    plan = heads(sec.group(1) if sec else t06, r"^#{3,4}\s+(\d+(?:-\d+)?\.\s+.+?)\s*$")
    got = heads(target, pat_target)
    if what == "06B":
        plan = [p for p in plan if re.match(r"\d+\.\s", p)]
    if plan == got:
        report("OK", "LOCKED", f"{what}의 장·절 {len(got)}개가 06과 같다")
        return
    report("FAIL", "LOCKED", f"{what} 장·절이 06과 다르다 (06 {len(plan)}개 · {what} {len(got)}개)")
    for a, b in zip(plan, got):
        if a != b:
            report("FAIL", "LOCKED", f"첫 차이: 06 「{a}」 ↔ {what} 「{b}」")
            break


def slides(text: str) -> list[tuple[int, str]]:
    parts = re.split(r"^## Slide\s+(\d+)[^\n]*$", text, flags=re.M)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def field(block: str, name: str) -> str:
    m = re.search(rf"^###\s*{name}\s*$(.*?)(?=^###\s|\Z)", block, re.S | re.M)
    return m.group(1).strip() if m else ""


def check_pack(pack: str, t06: str) -> None:
    ps, s06 = slides(pack), slides(t06)
    n_head = re.search(r"슬라이드 수:\s*(\d+)", pack)
    nums = [n for n, _ in ps]
    if n_head and int(n_head[1]) == len(ps) == len(s06) and nums == list(range(1, len(ps) + 1)):
        report("OK", "LOCKED", f"슬라이드 {len(ps)}장 — 헤더·06과 같다")
    else:
        report("FAIL", "LOCKED", f"슬라이드 수 불일치 — 헤더 {n_head[1] if n_head else '없음'} · 팩 {len(ps)} · 06 {len(s06)}")
    if "# 제작 지시" not in pack:
        report("FAIL", "형식", "`# 제작 지시`가 없다 — 도구가 프롬프트를 못 만든다")

    # 출처 표시: 아니오 인 장에 출처가 있으면 안 된다
    src_no = {n for n, b in s06 if re.search(r"출처 표시:\s*아니오", b)}
    for n, b in ps:
        src = field(b, "출처")
        if n in src_no and src and src != "없음":
            report("FAIL", "출처", f"Slide {n}: 06은 「출처 표시: 아니오」인데 출처가 있다")
        if re.search(r"\[S\d+\]|https?://", field(b, "제목") + field(b, "화면 문구") + src):
            report("FAIL", "출처", f"Slide {n}: 화면 필드에 근거 ID나 URL이 있다")
        title = {norm(x.lstrip("- ")) for x in field(b, "제목").splitlines() if x.strip()}
        lines = {norm(x.lstrip("- ")) for x in field(b, "화면 문구").splitlines() if x.strip()}
        if (title & lines) - {"없음"}:
            report("FAIL", "문구", f"Slide {n}: 제목과 화면 문구에 같은 줄이 있다")

    # Character Model — 모든 장에 글자 그대로 (E-036)
    cm = re.search(r"^- Character Model:(.*?)(?=^- \S|^## |\Z)", pack, re.S | re.M)
    models: dict[str, str] = {}
    if cm:
        for raw in [cm.group(1)] + cm.group(1).splitlines():
            raw = raw.strip().lstrip("- ").strip()
            parts = [p.strip() for p in raw.split(" · ")]
            if len(parts) >= 2 and not raw.startswith("없음"):
                models[parts[0]] = norm(" · ".join(p for p in parts[1:] if not p.startswith("외형 근거")))
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
    if len(args) != 2 or args[1].lower() not in {"06", "06b", "07"}:
        print(__doc__)
        return 2
    job, stage = args[0], args[1].lower()
    ws = ROOT / "작업" / job / "workspace"
    f = {k: latest(ws, v) for k, v in BASES.items()}
    if not f["05"] or not f["06"]:
        print(f"[중단] 05·06이 없다: {ws}")
        return 2
    read = lambda p: p.read_text(encoding="utf-8") if p else ""
    t00, t05, t06 = read(f["00"]), read(f["05"]), read(f["06"])
    head06 = t06.split("--- 헤더 끝 ---")[0]
    ppt = "PRESENTATION" in head06 or bool(slides(t06))

    if stage == "06":
        target_path = f["06"]
    elif ppt:
        target_path = f["pack"]
    else:
        target_path = f["06b_doc"] if stage == "06b" else f["07_doc"]
    if file_arg:
        target_path = Path(file_arg) if Path(file_arg).is_absolute() else ROOT / file_arg
    if not target_path or not target_path.exists():
        print(f"[중단] 대상 파일이 없다 ({stage})")
        return 2
    target = read(target_path)
    mode = "PRESENTATION" if ppt else "DOCUMENT"
    print(f"# gate_check · {job} · {stage} · {mode}\n대상 {target_path.name} · 근거 {f['05'].name} · 구조 {f['06'].name}\n")

    allowed = base_numbers(t00, t05) if stage == "06" else base_numbers(t00, t05, t06)
    check_numbers(target, allowed, skip_layout=ppt)
    check_remove(target, t05)

    if stage == "06":
        check_caution(target, t05, strict=not ppt)
        check_words(target, FORMAT_WORDS, "CHECK", "형식 이름", "형식 이름(E-026)", skip=r"^#|금지선|피할")
        check_words(target, VAGUE_WORDS, "CHECK", "판단 위임", "판단을 넘기는 말")
    elif ppt:
        check_pack(target, t06)
        check_caution(target, t05, strict=False)
        screen = "\n".join(field(b, k) for _, b in slides(target) for k in ("제목", "화면 문구", "한정"))
        check_words(screen, STRONG_WORDS, "CHECK", "강도", "화면 문구의 강도 후보")
    elif stage == "06b":
        check_doc_structure(t06, target, r"^##\s+(\d+\.\s+.+?)\s*$", "06B")
    else:
        check_doc_structure(t06, target, r"^#{2,3}\s+(\d+(?:-\d+)?\.\s+.+?)\s*$", "07")
        check_caution(target, t05, strict=True)
        check_words(target, STRONG_WORDS, "CHECK", "강도", "강도 후보", skip=r"^(title|subtitle|kind|date|org|accent)")

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
