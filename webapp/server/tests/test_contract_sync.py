"""프론트엔드(TypeScript)와 백엔드(Python)의 약속이 같은지 확인한다."""

import re
from pathlib import Path

from app import contract
from app.events import EVENT_TYPES

WEBAPP = Path(__file__).resolve().parents[2]


def test_event_types_match_frontend():
    source = (WEBAPP / "src" / "types" / "events.ts").read_text(encoding="utf-8")
    union = source.split("export type WorkflowEventPayload", 1)[1].split("export const", 1)[0]
    assert set(re.findall(r'type: "([a-z.]+)"', union)) == EVENT_TYPES


def test_default_agent_configs_match_frontend():
    source = (WEBAPP / "src" / "constants" / "agents.ts").read_text(encoding="utf-8")
    configs = re.findall(r'(\w+): \{\n.*?defaultConfig: \{ provider: "(\w+)", modelId: "([\w.-]+)", '
                         r'reasoningLevel: (?:"(\w+)"|null) \}', source, re.S)
    frontend = {agent: {"provider": provider, "modelId": model, "reasoningLevel": level or None}
                for agent, provider, model, level in configs}
    assert frontend == contract.DEFAULT_AGENT_CONFIGS


def test_stage_ids_match_frontend():
    source = (WEBAPP / "src" / "types" / "workflow.ts").read_text(encoding="utf-8")
    source = source.split("export type WorkflowStageId", 1)[1].split(";", 1)[0]
    assert tuple(re.findall(r'\| "(\w+)"', source)) == contract.STAGES


def test_contract_reading_rules():
    assert contract.verdict_from_05("검증 통과 — 조건부\n# Verified") == ("conditional", "검증 통과 — 조건부")
    assert contract.verdict_from_05("# 제목\n검증 통과 — 조건부") is None  # 첫 줄 계약을 지키지 않으면 판정하지 않는다
    assert contract.mode_from_brief("- 작업 ID: x / 모드: PRESENTATION / 작성일") == "presentation"
    assert contract.workspace_file("07_final_document.md", "auto").agent_id == "anya"
    assert contract.workspace_file("02_research_pack_v02.md", "document").version == 2
    assert contract.workspace_file("_입력_조사.md", "document") is None
    assert contract.is_finished("# x\n상태: 완료 (VER3)") and not contract.is_finished("# x\n상태: r2 발표팩 완료")


def test_needs_user_reads_status_line_not_sentence_shape():
    assert contract.needs_user("사용자 승인 대기 — 기획 확인")
    assert contract.needs_user("중단")
    assert contract.needs_user("검증 보류 — 사용자 결정 필요")
    assert not contract.needs_user("진행 중 02 조사")
    assert not contract.needs_user("진행 중 — 다음 단계로 넘어갈까요?")  # 질문형이어도 상태가 진행 중이면 계속
