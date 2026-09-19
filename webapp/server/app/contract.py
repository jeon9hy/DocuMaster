"""기존 DocuMaster 파일 계약을 웹앱 단계·에이전트로 읽는 규칙.

계약 자체(파일 번호·이름·05 첫 줄)는 루트 CLAUDE.md §4·§5와 .claude/로이드/실행.md가 정한다.
여기서는 그 계약을 **읽기만** 한다 — 계약을 바꾸는 코드를 두지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 프론트엔드 src/types/workflow.ts의 WorkflowStageId와 같은 순서·이름
STAGES = ("requirements", "planning", "research", "validation", "writing", "finalReview")

# 프론트엔드 src/constants/agents.ts의 defaultConfig와 같은 값(CLAUDE.md §1의 배치).
# Owner가 설정 화면에서 바꾸지 않으면 이 값으로 돈다(agent_settings.py). 유리·아냐는 서브에이전트라
# 추론 강도를 넘길 방법이 없다 → None(도구 기본값).
DEFAULT_AGENT_CONFIGS: dict[str, dict] = {
    # 로이드는 모델을 고정하지 않는다(사용자 지시) — claude CLI에 --model/--effort를 넘기지 않는다.
    "loid": {"provider": "anthropic", "modelId": "claude-code-default", "reasoningLevel": None},
    "yor": {"provider": "openai", "modelId": "gpt-5.6-sol", "reasoningLevel": "xhigh"},
    "yuri": {"provider": "anthropic", "modelId": "claude-sonnet-5", "reasoningLevel": None},
    "anya": {"provider": "anthropic", "modelId": "claude-opus-5", "reasoningLevel": None},
    "bond": {"provider": "google", "modelId": "notebooklm", "reasoningLevel": None},
}

# 05 첫 줄(CLAUDE.md §5)
VERDICT_BY_FIRST_LINE = {
    "검증 통과 — 이상 없음": "passed",
    "검증 통과 — 조건부": "conditional",
    "검증 보류 — 확인 불가": "blocked",
}

# 기본 목록에 보일 번호(지침서 §5.5). 나머지(03·04·06·옛 버전)는 internal.
PRIMARY_NUMBERS = {"00", "01", "02", "05", "07"}

_NUMBER_STAGE_AGENT = {
    "00": ("requirements", "loid"),
    "01": ("planning", "loid"),
    "02": ("research", "yor"),
    "03": ("validation", "yuri"),
    "04": ("validation", "yor"),
    "05": ("validation", "yuri"),
    "06": ("writing", "yor"),
    "07": ("writing", "yor"),  # 문서 모드의 07은 아냐가 쓴다(아래 workspace_file 참고)
}

_WORKSPACE_FILE = re.compile(r"^(?P<num>0[0-7])_(?P<base>.+?)(?:_v(?P<ver>\d+))?\.(?P<ext>md)$")
_MODE_LINE = re.compile(r"모드\s*[:：]\s*(DOCUMENT|PRESENTATION|문서|발표)")
_MODE_VALUE = {"DOCUMENT": "document", "문서": "document", "PRESENTATION": "presentation", "발표": "presentation"}


@dataclass(frozen=True)
class WorkspaceFile:
    number: str
    key: str  # 버전을 뺀 이름. 같은 key의 가장 높은 버전이 최신
    version: int
    stage_id: str
    agent_id: str


def workspace_file(name: str, mode: str) -> WorkspaceFile | None:
    """workspace/ 안의 계약 파일이면 해석 결과를, 아니면 None."""
    match = _WORKSPACE_FILE.match(name)
    if not match:
        return None
    number = match["num"]
    stage_id, agent_id = _NUMBER_STAGE_AGENT[number]
    if number == "07" and (mode == "document" or name.startswith("07_final_document")):
        agent_id = "anya"
    return WorkspaceFile(
        number=number,
        key=f"{number}_{match['base']}",
        version=int(match["ver"] or 1),
        stage_id=stage_id,
        agent_id=agent_id,
    )


def mode_from_brief(text: str) -> str | None:
    """00 헤더의 `모드: DOCUMENT|PRESENTATION`. 없으면 None."""
    match = _MODE_LINE.search(text[:2000])
    return _MODE_VALUE[match[1]] if match else None


def verdict_from_05(text: str) -> tuple[str, str] | None:
    """05 첫 줄 → (판정, 첫 줄). 첫 줄이 계약과 다르면 None."""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    verdict = VERDICT_BY_FIRST_LINE.get(first_line)
    return (verdict, first_line) if verdict else None


def status_line(state_md: str) -> str:
    """상태.md의 `상태:` 줄(CLAUDE.md §6 — 첫 3줄에 둔다)."""
    for line in state_md.splitlines()[:5]:
        if line.startswith("상태:"):
            return line.removeprefix("상태:").strip()
    return ""


def is_finished(state_md: str) -> bool:
    return status_line(state_md).startswith("완료")


def needs_user(status: str) -> bool:
    """상태 줄이 사람의 개입을 기다리는지(상태파일.md: `사용자 승인 대기` · `중단`, 검증 `보류`)."""
    waiting = "대기" in status and any(word in status for word in ("사용자", "승인", "결정", "입력"))
    return waiting or status.startswith("중단") or "보류" in status or "blocked" in status.lower()


def current_worker(numbers: set[str], mode: str, has_visual: bool) -> tuple[str, str]:
    """이미 있는 파일 번호로 지금 일하는 (단계, 에이전트)를 정한다. 파일 순서가 곧 계약이다."""
    if "00" not in numbers:
        return "requirements", "loid"
    if "01" not in numbers:
        return "planning", "loid"
    if "02" not in numbers:
        return "research", "yor"
    if "03" not in numbers:
        return "validation", "yuri"
    if "04" not in numbers:
        return "validation", "yor"
    if "05" not in numbers:
        return "validation", "yuri"
    if "06" not in numbers:
        return "writing", "yor"
    if "07" not in numbers:
        # 문서: 06B(비주얼) 뒤 아냐가 07. 발표: 06B가 곧 07 발표팩(요르)
        if mode == "document" and has_visual:
            return "writing", "anya"
        return "writing", "yor"
    return "finalReview", "loid"
