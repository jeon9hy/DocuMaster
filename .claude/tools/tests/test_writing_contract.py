"""글 목적과 편집의 독립성·이전 결과물 호환·실제 게이트 경로를 임시 자료로 검증한다."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load("gate_check")
renderer = load("md2html")


def brief(purpose="설명·해설", style="단정"):
    return (f"# User Brief\n- 모드: DOCUMENT\n- 글 유형: {purpose} — 선택 이유\n"
            "- 독자 도달점: 개념 이해 / 완료 기준: 예시와 연결\n"
            f"- 보조 목적: 없음 / 편집: {style}\n--- 헤더 끝 ---\n")


def document(purpose="설명·해설", style="단정"):
    return (f"---\ntitle: 예시 글\ntype: 글\npurpose: {purpose}\nstyle: {style}\n"
            "cover: false\naccent: '#1F5F6B'\n---\n\n"
            "## 개념\n자료의 정의다.[S01]\n\n::: sources 출처\n"
            "S01 | 자료명 | 기관 | 미상 | [원문](https://example.com)\n:::\n")


class WritingContractTests(unittest.TestCase):
    def setUp(self):
        gate.results.clear()
        renderer.WARNINGS.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def failures(self):
        return [r for r in gate.results if r[0] == "FAIL"]

    def render(self, text):
        source, output = self.root / "source.md", self.root / "output.html"
        source.write_text(text, encoding="utf-8")
        with patch("sys.argv", ["md2html.py", str(source), str(output)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(renderer.main(), 0)
        return output.read_text(encoding="utf-8")

    def test_all_purposes_validate_and_render_in_either_style(self):
        for purpose in gate.DOC_PURPOSES:
            for style in gate.DOC_STYLES:
                with self.subTest(purpose=purpose, style=style):
                    gate.results.clear()
                    renderer.WARNINGS.clear()
                    text = document(purpose, style)
                    gate.check_doc_type(brief(purpose, style), text, self.root)
                    self.assertFalse(self.failures())
                    html = self.render(text)
                    self.assertEqual('<body class="read">' in html, style == "부드러움")
                    self.assertIn('href="#source-S01"', html)
                    self.assertIn('id="source-S01"', html)
                    self.assertFalse(renderer.WARNINGS)

    def test_mismatched_purpose_and_style_fail_independently(self):
        gate.check_doc_type(brief(), document("분석", "부드러움"), self.root)
        self.assertEqual({r[1] for r in self.failures()}, {"글 유형", "편집"})

    def test_new_contract_rejects_missing_unknown_and_partial_metadata(self):
        variants = [document().replace("type: 글", "type: 보고서"),
                    document().replace("purpose: 설명·해설\n", ""),
                    document().replace("purpose: 설명·해설", "purpose: 설명·해설형"),
                    document().replace("purpose: 설명·해설", "purpose: 설명·해설 잘못된값"),
                    document().replace("style: 단정\n", ""),
                    document().replace("style: 단정", "style: 기타"), "본문만"]
        for text in variants:
            with self.subTest(text=text[:90]):
                gate.results.clear()
                gate.check_doc_type(brief(), text, self.root)
                self.assertTrue(self.failures())

    def test_missing_or_invalid_brief_does_not_default_to_analysis(self):
        for text in [brief().replace("글 유형: 설명·해설", "글 유형:"),
                     brief("보고서"), "# Brief\n- 모드: DOCUMENT\n"]:
            with self.subTest(text=text):
                gate.results.clear()
                gate.check_doc_type(text, document(), self.root)
                self.assertTrue(self.failures())

    def test_quoted_crlf_and_bom_metadata_match_renderer(self):
        text = "\ufeff" + document().replace("purpose: 설명·해설", "purpose: '설명·해설'").replace("style: 단정", 'style: "단정"').replace("\n", "\r\n")
        gate.check_doc_type(brief(), text, self.root)
        self.assertFalse(self.failures())
        self.assertIn("<body>", self.render(text))

    def test_legacy_files_keep_their_layout_and_contract(self):
        for kind in ("보고서", "읽을거리"):
            with self.subTest(kind=kind):
                gate.results.clear()
                text = f"---\ntitle: 이전 글\ntype: {kind}\naccent: #1F5F6B\ncover: false\n---\n본문"
                gate.check_doc_type(f"- 문서 유형: {kind}\n--- 헤더 끝 ---", text, self.root)
                self.assertFalse(self.failures())
                self.assertEqual('<body class="read">' in self.render(text), kind == "읽을거리")
        gate.results.clear()
        gate.check_doc_type("- 문서 유형: 보고서", text, self.root)
        self.assertTrue(self.failures())

    def test_legitimate_explanation_and_procedure_are_reviewed_not_deleted(self):
        gate.check_hedges("상관관계는 인과관계가 아니다.\n접수가 확인되지 않았다면 상태를 확인한다.")
        self.assertFalse(self.failures())
        self.assertTrue(any(r[0] == "CHECK" and r[1] == "해명 문장" for r in gate.results))

    def test_shared_source_is_reviewed_at_claim_level(self):
        pack = "### REMOVE\n| 항목(근거 ID) | 삭제 사유 | 영향 |\n| --- | --- | --- |\n| S01 과도한 주장 | 근거 부족 | 제외 |"
        gate.check_remove("다른 채택된 사실.[S01]", pack, strict=False)
        self.assertFalse(self.failures())
        self.assertTrue(any(r[0] == "CHECK" and r[1] == "REMOVE" for r in gate.results))
        gate.results.clear()
        gate.check_remove("제거된 발표 주장.[S01]", pack)
        self.assertTrue(self.failures())

    def test_verified_legal_condition_is_reviewed_but_missing_source_still_fails(self):
        pack = ("## 2. 검증된 사실\n해당 행위는 금지된다.[S01]\n"
                "## 5. 출처\n- S01 | 자료명 | 기관 | 미상 | https://example.com\n")
        gate.check_05(pack)
        self.assertFalse(self.failures())
        self.assertTrue(any(r[0] == "CHECK" and r[1] == "05 §2" for r in gate.results))
        gate.results.clear()
        gate.check_05(pack.replace("https://example.com", ""))
        self.assertTrue(self.failures())

    def test_source_id_is_not_mistaken_for_internal_file_reference(self):
        self.assertIsNone(gate.DIRECTIVE_WORDS.search("S04의 정의를 따른 사실"))
        self.assertIsNotNone(gate.DIRECTIVE_WORDS.search("04의 설명을 참고"))

    def test_sources_and_image_exclusions_remain_failures(self):
        gate.check_doc_sources("근거.[S02]\n::: sources 출처\nS01 | 자료 | 기관 | 미상 | https://example.com\n:::")
        self.assertTrue(self.failures())
        gate.results.clear()
        (self.root / "references").mkdir()
        (self.root / "references/images.md").write_text("| I01 | ../sources/images/a.png | 장면 | 권리자 | URL | 제외 |\n", encoding="utf-8")
        gate.check_doc_type(brief(), document() + '\n![그림](../sources/images/a.png)', self.root)
        self.assertTrue(any(r[1] == "그림" for r in self.failures()))

    def test_cli_path_checks_new_contract_in_temporary_workspace(self):
        ws = self.root / "작업" / "fixture" / "workspace"
        ws.mkdir(parents=True)
        (ws.parent / "상태.md").write_text("## 세션 yor=fixture · 유리 에이전트=fixture · 아냐 에이전트=fixture\n", encoding="utf-8")
        (ws / "00_user_brief.md").write_text(brief(), encoding="utf-8")
        (ws / "05_verified_research_pack.md").write_text(
            "검증 통과 — 이상 없음\n- REMOVE 0 · CAUTION 0\n--- 헤더 끝 ---\n"
            "## 2. 검증된 사실\n자료의 정의다.[S01]\n## 5. 출처\n"
            "- S01 | 자료명 | 기관 | 미상 | https://example.com\n", encoding="utf-8")
        (ws / "07_final_document.md").write_text(document(), encoding="utf-8")
        with patch.object(gate, "ROOT", self.root), patch("sys.argv", ["gate_check.py", "fixture", "07"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gate.main(), 0)
            gate.results.clear()
            (ws / "07_final_document.md").write_text(document("분석"), encoding="utf-8")
            self.assertEqual(gate.main(), 1)

    def test_research_process_voice_is_flagged_separately(self):
        gate.check_hedges("민간 배점은 확인하지 못했다.\n아래 표는 이 가이드가 정리한 전망이다.\n"
                          "이 수치는 조심해서 읽어야 한다.\n::: note\n민간 배점은 이 표에 없다.\n:::")
        process = [r for r in gate.results if r[1] == "조사 시점"]
        self.assertEqual(len(process), 3)
        self.assertFalse(self.failures())

    def test_reader_actions_and_note_are_not_process_voice(self):
        gate.check_hedges("기록물은 열람실에서 열람한다.\n접수 뒤 문자로 결과를 확인한다.\n"
                          "::: note\n신입 초봉 비교는 이 표에 없다.\n:::")
        self.assertFalse([r for r in gate.results if r[1] == "조사 시점"])

    def test_same_ending_three_times_in_a_row_is_flagged(self):
        gate.check_endings("세계는 현실과 닮은 환상 세계라고 알려져 있어요.\n"
                           "주민들은 일해서 번 돈으로 물건을 사고 있어요.\n"
                           "그 옆에는 갑자기 나타나는 괴물도 있어요.\n")
        self.assertIn("3연속", " ".join(r[2] for r in gate.results if r[1] == "어미"))

    def test_polite_style_without_varied_endings_is_flagged(self):
        plain = "작고 둥근 인물들이 풀을 뽑아 돈을 버는 이야기예요.\n\n"
        varied = "작고 둥근 인물들이 풀을 뽑아 돈을 버는 이야기거든요.\n\n"
        gate.check_endings(plain * 30)
        self.assertTrue([r for r in gate.results if r[1] == "어미" and "평서 어미만" in r[2]])
        gate.results.clear()
        gate.check_endings(plain * 20 + varied * 10)
        self.assertFalse([r for r in gate.results if r[1] == "어미" and "평서 어미만" in r[2]])

    def test_short_documents_are_not_judged_on_ending_share(self):
        gate.check_endings("치이카와는 나가노가 그린 만화로 알려져 있어요.\n\n"
                           "단행본과 애니메이션으로도 이어진 작품이에요.\n")
        self.assertFalse([r for r in gate.results if r[1] == "어미" and "쏠렸다" in r[2]])

    def test_note_collected_at_document_end_is_flagged(self):
        self.assertTrue(gate.ends_with_note("본문이다.\n::: note\n한계 문장.\n:::\n"))
        self.assertFalse(gate.ends_with_note("본문이다.\n::: note\n한계 문장.\n:::\n\n이어지는 본문이다.\n"))
        self.assertFalse(gate.ends_with_note("본문만 있다.\n"))

    def test_every_registered_purpose_has_a_loadable_profile(self):
        index = (ROOT / ".claude/공통/글유형.md").read_text(encoding="utf-8")
        for purpose in gate.DOC_PURPOSES:
            name = "글_" + purpose.replace("·", "") + ".md"
            self.assertIn(name, index)
            profile = (ROOT / ".claude/공통" / name).read_text(encoding="utf-8")
            self.assertIn("## 완료 기준", profile)
            self.assertIn("## 기획·조사 재료", profile)
            self.assertLessEqual(len(profile.encode("utf-8")), 6000)


if __name__ == "__main__":
    unittest.main()
