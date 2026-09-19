"""요르의 수정 패치를 조사 문서에 적용한다.

왜 이게 있는가 — 지적이 한 건이어도 조사 전문을 다시 출력하면 그게 가장 큰 토큰 누수다.
그렇다고 패치를 손으로 적용하면 조용히 엉뚱한 곳이 바뀔 수 있다. 그래서 **기계가 적용하고,
조금이라도 애매하면 아무것도 쓰지 않고 멈춘다.**

사용:
    python .claude/tools/apply_patch.py <원본> <출력> <04_raw.md>
    python .claude/tools/apply_patch.py --check <원본> <04_raw.md>
    --answers <04_verification_answers.md> 를 붙이면 응답 블록도 그 경로에 저장한다(응답과 패치를 한 번에)

규칙(`.claude/요르/검증응답.md` 와 같은 계약):
  · `OLD:` 는 원본에 **정확히 한 번** 나타나야 한다. 0번이나 2번 이상이면 전체 실패.
  · 하나라도 실패하면 **출력 파일을 쓰지 않는다.** 부분 적용은 가장 나쁜 결과다.
  · 문서의 절반 이상이 바뀌면 경고한다 — 그 경우 전문 재출력이 맞다.
"""
from __future__ import annotations

import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 저장 뒤 죽지 않게(E-024)
except Exception:
    pass

RESP_A, RESP_B = "=== 응답 시작 ===", "=== 응답 끝 ==="
PATCH_A, PATCH_B = "=== 수정 패치 시작 ===", "=== 수정 패치 끝 ==="
FULL_A, FULL_B = "=== 수정 조사 전문 시작 ===", "=== 수정 조사 전문 끝 ==="


def cut(raw: str, a: str, b: str):
    m = re.search(re.escape(a) + r"(.*?)" + re.escape(b), raw, re.S)
    return m.group(1).strip() if m else None


def parse_patches(block: str):
    """--- PATCH n --- … --- PATCH 끝 --- 을 (meta, old, new) 목록으로."""
    out = []
    for chunk in re.findall(r"---\s*PATCH\s+\S+?\s*---(.*?)---\s*PATCH\s*끝\s*---",
                            block, re.S):
        m = re.search(r"^OLD:\s*?\n(.*?)^NEW:\s*?\n(.*?)\Z", chunk, re.S | re.M)
        if not m:
            out.append((chunk.strip()[:80], None, None))
            continue
        meta = chunk[:m.start()].strip()
        out.append((meta, m.group(1).rstrip("\n"), m.group(2).rstrip("\n")))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:]]
    answers_path = None
    if "--answers" in args:
        i = args.index("--answers")
        answers_path = args[i + 1]
        del args[i:i + 2]
    check_only = "--check" in args
    if check_only:
        args.remove("--check")
        if len(args) != 2:
            print("사용: --check <원본> <04_raw.md>")
            return 2
        src_path, raw_path = args
        out_path = None
    else:
        if len(args) != 3:
            print("사용: <원본> <출력> <04_raw.md>")
            return 2
        src_path, out_path, raw_path = args

    raw = open(raw_path, encoding="utf-8").read()
    src = open(src_path, encoding="utf-8").read()

    resp = cut(raw, RESP_A, RESP_B)
    if resp is None:
        print("[실패] 응답 구분자가 없다 — 요르에게 형식을 지켜 다시 내라고 한다(1회만).")
        return 1
    if answers_path and not check_only:
        open(answers_path, "w", encoding="utf-8").write(resp + "\n")
        print("[저장] 응답", answers_path)

    full = cut(raw, FULL_A, FULL_B)
    patch_block = cut(raw, PATCH_A, PATCH_B)

    if full:
        print("[전문] 요르가 전문 재출력을 선택했다. 사유 줄을 확인하고 그대로 저장한다.")
        print("      첫 줄:", full.splitlines()[0][:100] if full.splitlines() else "")
        if out_path:
            open(out_path, "w", encoding="utf-8").write(full + "\n")
            print("[저장]", out_path)
        return 0

    if patch_block is None:
        print("[실패] 패치 구분자도 전문 구분자도 없다 — 형식 재요청(1회만).")
        return 1

    if patch_block.strip() == "수정 없음":
        print("[수정 없음] 이전 버전을 계속 쓴다. 새 파일을 만들지 않는다.")
        return 0

    patches = parse_patches(patch_block)
    if not patches:
        print("[실패] 패치 블록은 있는데 PATCH 항목을 못 읽었다 — 형식 재요청(1회만).")
        return 1

    # 1단계: 전부 검증한다. 하나라도 실패하면 아무것도 쓰지 않는다.
    errors, plan = [], []
    for i, (meta, old, new) in enumerate(patches, start=1):
        head = f"PATCH {i} ({meta.splitlines()[0][:50] if meta else ''})"
        if old is None:
            errors.append(f"{head}: OLD/NEW 를 못 읽었다")
            continue
        if not old.strip():
            errors.append(f"{head}: OLD 가 비었다")
            continue
        n = src.count(old)
        if n == 0:
            errors.append(f"{head}: OLD 가 원본에 없다 — 첫 줄 {old.splitlines()[0][:60]!r}")
        elif n > 1:
            errors.append(f"{head}: OLD 가 {n}번 나타난다(유일해야 한다) — "
                          f"앞뒤 줄을 더 붙여 달라고 한다")
        else:
            plan.append((head, old, new))

    if errors:
        print("[실패] 적용하지 않았다. 아래를 요르에게 그대로 돌려준다:")
        for e in errors:
            print("  -", e)
        return 1

    # 2단계: 순서대로 적용한다. 각 OLD 는 이 시점에도 유일해야 한다.
    cur = src
    for head, old, new in plan:
        if cur.count(old) != 1:
            print(f"[실패] {head}: 앞 패치가 적용된 뒤 OLD 가 유일하지 않게 됐다. "
                  f"아무것도 쓰지 않았다.")
            return 1
        cur = cur.replace(old, new, 1)

    changed = sum(len(o) for _, o, _ in plan)
    ratio = changed / max(len(src), 1)
    print(f"[검증 통과] 패치 {len(plan)}건 · 원문의 약 {ratio:.0%} 를 건드린다")
    if ratio > 0.5:
        print("[경고] 절반 이상이 바뀐다 — 패치보다 전문 재출력이 맞는 상황일 수 있다.")

    if check_only:
        print("[--check] 실제로 쓰지 않았다.")
        return 0

    open(out_path, "w", encoding="utf-8").write(cur)
    print("[저장]", out_path)
    print("※ 저장 뒤 반드시 확인한다 — 헤더의 근거 확인 수치, 절 간 값 일치.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
