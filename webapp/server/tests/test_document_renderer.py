"""문서 지침의 citation·sources 마크업이 최종 HTML까지 유지되는지 확인한다."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[3] / ".claude" / "tools" / "md2html.py"
SPEC = importlib.util.spec_from_file_location("documaster_md2html", MODULE_PATH)
assert SPEC and SPEC.loader
md2html = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(md2html)


def test_citation_links_to_rendered_source_row():
    body = "S01 | 자료명 | 기관 | 2026-09-22 | [원문](https://example.com)"
    citation = md2html.inline("근거가 있다.[S01]")
    sources = md2html.render_block("sources", "출처", [body], "#123456")

    assert 'href="#source-S01">1</a>' in citation
    assert 'id="source-S01"' in sources
    assert "자료명 · 기관 · 2026-09-22" in sources
    assert 'href="https://example.com"' in sources


def test_adjacent_citations_share_one_superscript():
    # [S01][S02]가 "12"로 붙어 보이면 출처 12로 오해한다 — 한 위첨자에 쉼표로 묶는다
    html = md2html.inline("근거가 있다.[S01][S02] 다음.[S09][S10]")
    assert 'href="#source-S01">1</a>,<a href="#source-S02">2</a></sup>' in html
    assert 'href="#source-S09">9</a>,<a href="#source-S10">10</a></sup>' in html
    assert html.count('<sup class="cite">') == 2


def test_sources_always_start_on_a_new_page():
    # 본문 끝에 붙으면 쪽 경계에서 출처 목록이 잘린다 — 항상 새 쪽에서 시작한다
    rule = next(line for line in md2html.CSS.splitlines() if line.startswith(".sources {"))
    assert "page-break-before: always" in rule and "break-before: page" in rule


def test_front_matter_title_is_visible_without_cover(tmp_path, monkeypatch):
    source = tmp_path / "memo.md"
    output = tmp_path / "memo.html"
    source.write_text("---\ntitle: 판단 메모\ncover: false\naccent: #1F5F6B\n---\n\n첫 문단", encoding="utf-8")
    monkeypatch.setattr("sys.argv", [str(MODULE_PATH), str(source), str(output)])

    assert md2html.main() == 0
    rendered = output.read_text(encoding="utf-8")
    assert "<h1>판단 메모</h1>" in rendered


def test_math_renders_as_mathml_and_leaves_money_and_code_alone():
    inline = md2html.inline(r"계수 $K_a = \frac{1-\sin\phi}{1+\sin\phi}$, 금액 $5와 $10, 코드 `$x$`")
    assert inline.count("<math") == 1 and "<mfrac>" in inline
    assert "$5와 $10" in inline and "<code>$x$</code>" in inline
    md2html.WARNINGS.clear()
    assert "<code>" in md2html.math_html("x^")  # 못 바꾸는 식은 경고 + 코드 조각
    assert any("수식 변환 실패" in warning for warning in md2html.WARNINGS)
    md2html.WARNINGS.clear()
