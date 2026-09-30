"""조사 수집 그림 — 02 §I의 이미지 후보를 내려받아 아냐가 쓸 목록과 로이드가 볼 모아보기를 만든다.

사용:
    python .claude/tools/fetch_images.py <작업ID> [--force]

요르(Codex)는 읽기 전용이라 파일을 못 받는다 — 02 §I에 URL만 적고, 이 도구가 받는다.
만드는 것:
  작업/<ID>/sources/images/I01.jpg …        긴 변 1600px 이하로 줄인 파일
  작업/<ID>/references/images.md            | ID | 경로 | 무엇 | 크레디트 | 출처 페이지 | 상태 | 쓸 곳 |
  작업/<ID>/references/images_contact.png   번호·설명을 단 모아보기 — 로이드가 캡션과 그림이 맞는지 본다
images.md가 이미 있으면(로이드가 `제외`로 고친 뒤) 덮어쓰지 않는다. 다시 받으려면 --force.
종료 코드: 0 한 장 이상 받음 · 1 한 장도 못 받음 · 2 입력 없음
"""
from __future__ import annotations

import io
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔(E-005)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
MAX_SIDE = 1600


def latest_02(ws: Path) -> Path | None:
    cands = [p for p in ws.glob("02_research_pack*.md") if re.fullmatch(r"02_research_pack(_v\d+)?\.md", p.name)]
    return max(cands, key=lambda p: int((re.search(r"_v(\d+)\.md$", p.name) or [0, 1])[1]), default=None)


def rows_of_section_i(text: str) -> list[list[str]]:
    m = re.search(r"^## I\.[^\n]*\n(.*?)(?=^## [A-Z]\.|\Z)", text, re.S | re.M)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"I\d{2}", cells[0]) and len(cells) >= 5:
            rows.append((cells + [""] * 6)[:6])
    return rows


def download(url: str, referer: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer or url,
                                               "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read()
    except urllib.error.HTTPError:
        # 위키미디어 썸네일은 정해진 크기만 준다(400) — 원본 주소로 한 번 더
        m = re.match(r"(https://upload\.wikimedia\.org/.+?)/thumb/(.+)/[^/]+$", url)
        if not m:
            raise
        return download(f"{m[1]}/{m[2]}", referer)


def save_image(data: bytes, dest_stem: Path) -> Path:
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    im.load()
    if max(im.size) < 200:
        raise ValueError(f"너무 작다 {im.size[0]}x{im.size[1]}")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha:
        out = dest_stem.with_suffix(".png")
        im.convert("RGBA").save(out, optimize=True)
    else:
        out = dest_stem.with_suffix(".jpg")
        im.convert("RGB").save(out, quality=86, optimize=True)
    return out


def font(size: int):
    from PIL import ImageFont
    for d in (os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"), r"C:\Windows\Fonts"):
        for name in ("Pretendard-Regular.ttf", "malgun.ttf"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def contact_sheet(items: list[tuple[str, Path, str]], out: Path) -> None:
    from PIL import Image, ImageDraw
    cell, label_h, cols = 300, 46, 4
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), "white")
    draw, f = ImageDraw.Draw(sheet), font(15)
    for i, (iid, path, what) in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
        im = Image.open(path).convert("RGB")
        im.thumbnail((cell - 12, cell - 12))
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        draw.text((x + 8, y + cell + 2), f"{iid} {what}"[:24], fill="black", font=f)
        draw.text((x + 8, y + cell + 22), f"{what}"[24:48], fill="black", font=f)
    sheet.save(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    job = ROOT / "작업" / args[0]
    ws = job / "workspace"
    p02 = latest_02(ws)
    if not p02:
        print(f"[중단] 02가 없다: {ws}")
        return 2
    rows = rows_of_section_i(p02.read_text(encoding="utf-8"))
    if not rows:
        print(f"[중단] {p02.name}에 `## I.` 이미지 후보 표가 없다 — 요르 patch로 §I를 받는다")
        return 2
    listing = job / "references" / "images.md"
    if listing.exists() and "--force" not in sys.argv:
        print(f"[중단] {listing} 가 이미 있다(로이드 수정 보존) — 다시 받으려면 --force")
        return 2
    img_dir = job / "sources" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    listing.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# 이미지 목록 — 경로는 workspace의 07 기준. `제외`·`실패`는 쓰지 않는다",
             "", "| ID | 경로 | 무엇 | 크레디트 | 출처 페이지 | 상태 | 쓸 곳 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    ok: list[tuple[str, Path, str]] = []
    for iid, url, page, what, rights, where in rows:
        url = re.sub(r"^<|>$", "", url)
        try:
            saved = save_image(download(url, page), img_dir / iid)
            rel = "../sources/images/" + saved.name
            state = "사용"
            ok.append((iid, saved, what))
            print(f"OK   {iid} {saved.name} — {what}")
        except Exception as e:  # 받기·열기 실패는 목록에 이유를 남기고 넘어간다
            rel, state = "-", f"실패: {type(e).__name__} {str(e)[:40]}"
            print(f"FAIL {iid} {state} — {url[:70]}")
        lines.append(f"| {iid} | {rel} | {what} | © {rights} | {page} | {state} | {where} |")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if ok:
        contact = job / "references" / "images_contact.png"
        contact_sheet(ok, contact)
        print(f"\n모아보기: {contact}")
    print(f"목록: {listing}\n결과: 받음 {len(ok)} · 실패 {len(rows) - len(ok)} — 모아보기를 보고 캡션과 다른 그림은 `제외`로 바꾼다")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
