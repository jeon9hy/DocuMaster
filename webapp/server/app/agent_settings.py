"""에이전트 모델·추론 강도 설정(전역). Owner만 바꾸고, 앱·오케스트레이터는 바꾸지 않는다.

선택지는 **실제로 호출에 넘길 수 있는 값만** 둔다 — 화면에서만 바뀌는 설정을 만들지 않는다.
- 로이드: 어댑터가 `claude -p --model/--effort`로 넘긴다(claude --help 2.1.278).
- 요르: Codex CLI가 로컬에 받아 둔 모델 목록(~/.codex/models_cache.json)의 모델·지원 추론 강도. 없으면 기본값만.
- 유리·아냐: 로이드가 부르는 서브에이전트(Agent 도구)의 model 값(sonnet·opus·haiku·fable).
  서브에이전트 호출에는 추론 강도를 넘길 방법이 없어 「도구 기본값」 하나뿐이다.
- 본드: NotebookLM(nlm CLI)에는 모델 선택이 없다.

요르·유리·아냐 값은 실행마다 JSON 파일로 쓰고 환경변수 DOCUMASTER_AGENT_MODELS로 로이드에게 알린다
(루트 .claude/로이드/실행.md §3). 실행 뒤 실행 기록에서 실제 호출 값을 대조해 다르면 경고한다(check_model_calls).

지원하지 않는 값은 거절한다. 다른 값으로 조용히 바꾸지 않는다.
실행은 시작할 때 설정을 스냅샷으로 고정한다(runs.agent_config_json) — 실행 중 바꾼 값은 다음 실행부터 적용된다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import contract
from .db import Database, now_iso

UNSUPPORTED_MESSAGE = "현재 선택한 모델 설정을 사용할 수 없습니다."

# 로이드가 고를 수 있는 모델. claude-code-default = --model을 넘기지 않음(사용자의 Claude Code 기본값).
_LOID_MODELS = ("claude-code-default", "claude-fable-5-1", "claude-opus-5", "claude-sonnet-5")
# None = --effort를 넘기지 않음(Claude Code 기본값)
_LOID_REASONING = (None, "low", "medium", "high", "xhigh", "max")

# 서브에이전트(Agent 도구)의 model 값. 화면의 모델 ID → 도구에 넘기는 별칭
SUBAGENT_ALIAS = {
    "claude-fable-5-1": "fable",
    "claude-opus-5": "opus",
    "claude-sonnet-5": "sonnet",
    "claude-haiku-4-5": "haiku",
}

_LOCK_REASON = {"bond": "NotebookLM(nlm CLI)에는 모델 선택이 없습니다."}


class UnsupportedConfigError(ValueError):
    pass


def codex_models(codex_home: Path | None) -> dict[str, list[str]]:
    """Codex CLI가 받아 둔 모델 목록(목록에 보이는 것만) → 모델별 지원 추론 강도. 못 읽으면 기본값 하나."""
    default = contract.DEFAULT_AGENT_CONFIGS["yor"]
    fallback = {default["modelId"]: [default["reasoningLevel"]]}
    try:
        data = json.loads((codex_home / "models_cache.json").read_text(encoding="utf-8")) if codex_home else {}
    except (OSError, ValueError):
        return fallback
    models: dict[str, list[str]] = {}
    for model in data.get("models", []) if isinstance(data, dict) else []:
        if not isinstance(model, dict) or model.get("visibility") != "list" or not model.get("slug"):
            continue
        levels = [level.get("effort") if isinstance(level, dict) else level
                  for level in model.get("supported_reasoning_levels") or []]
        levels = [level for level in levels if isinstance(level, str)]
        if levels:
            models[str(model["slug"])] = levels
    return models or fallback


def options_for(agent_id: str, codex_home: Path | None) -> dict:
    default = contract.DEFAULT_AGENT_CONFIGS[agent_id]
    if agent_id == "loid":
        return {"modelIds": list(_LOID_MODELS), "reasoningLevels": list(_LOID_REASONING),
                "reasoningByModel": None, "lockedReason": None}
    if agent_id == "yor":
        models = codex_models(codex_home)
        levels = sorted({level for values in models.values() for level in values}, key=_level_order)
        return {"modelIds": list(models), "reasoningLevels": levels, "reasoningByModel": models, "lockedReason": None}
    if agent_id in ("yuri", "anya"):
        return {"modelIds": list(SUBAGENT_ALIAS), "reasoningLevels": [None], "reasoningByModel": None,
                "lockedReason": None}
    return {"modelIds": [default["modelId"]], "reasoningLevels": [default["reasoningLevel"]],
            "reasoningByModel": None, "lockedReason": _LOCK_REASON[agent_id]}


_LEVELS = ("low", "medium", "high", "xhigh", "max", "ultra")


def _level_order(level: str) -> int:
    return _LEVELS.index(level) if level in _LEVELS else len(_LEVELS)


def is_supported(agent_id: str, config: dict, codex_home: Path | None) -> bool:
    default = contract.DEFAULT_AGENT_CONFIGS.get(agent_id)
    if default is None or config.get("provider") != default["provider"]:
        return False
    options = options_for(agent_id, codex_home)
    if config.get("modelId") not in options["modelIds"]:
        return False
    by_model = options["reasoningByModel"]
    allowed = by_model[config["modelId"]] if by_model else options["reasoningLevels"]
    return config.get("reasoningLevel") in allowed


class AgentSettingsService:
    def __init__(self, db: Database, codex_home: Path | None = None):
        self._db = db
        self._codex_home = codex_home

    def _overrides(self) -> dict[str, dict]:
        return {row["agent_id"]: dict(row) for row in self._db.query("SELECT * FROM agent_overrides")}

    def effective(self) -> dict[str, dict]:
        """실행에 넘길 설정. Owner가 바꾸지 않은 에이전트는 기본 배치 그대로."""
        overrides = self._overrides()
        result = {}
        for agent_id, default in contract.DEFAULT_AGENT_CONFIGS.items():
            row = overrides.get(agent_id)
            result[agent_id] = dict(default) if row is None else {
                "provider": row["provider"], "modelId": row["model_id"], "reasoningLevel": row["reasoning_level"]}
        return result

    def list(self) -> list[dict]:
        overrides = self._overrides()
        effective = self.effective()
        return [{
            "agentId": agent_id,
            "config": effective[agent_id],
            "defaultConfig": default,
            "overridden": agent_id in overrides,
            "updatedAt": overrides[agent_id]["updated_at"] if agent_id in overrides else None,
            **options_for(agent_id, self._codex_home),
        } for agent_id, default in contract.DEFAULT_AGENT_CONFIGS.items()]

    def update(self, agent_id: str, config: dict) -> None:
        if agent_id not in contract.DEFAULT_AGENT_CONFIGS:
            raise KeyError(agent_id)
        if not is_supported(agent_id, config, self._codex_home):
            raise UnsupportedConfigError(UNSUPPORTED_MESSAGE)
        default = contract.DEFAULT_AGENT_CONFIGS[agent_id]
        if (config["modelId"], config["reasoningLevel"]) == (default["modelId"], default["reasoningLevel"]):
            self.reset(agent_id)
            return
        self._db.execute(
            "INSERT INTO agent_overrides VALUES (?, ?, ?, ?, ?) ON CONFLICT(agent_id) DO UPDATE SET"
            " provider = excluded.provider, model_id = excluded.model_id,"
            " reasoning_level = excluded.reasoning_level, updated_at = excluded.updated_at",
            (agent_id, config["provider"], config["modelId"], config["reasoningLevel"], now_iso()),
        )

    def reset(self, agent_id: str) -> None:
        if agent_id not in contract.DEFAULT_AGENT_CONFIGS:
            raise KeyError(agent_id)
        self._db.execute("DELETE FROM agent_overrides WHERE agent_id = ?", (agent_id,))

    def snapshot_json(self) -> str:
        return json.dumps(self.effective(), ensure_ascii=False)


def load_snapshot(raw: str | None) -> dict[str, dict]:
    """runs.agent_config_json → 설정. 스냅샷이 없는 옛 실행은 기본 배치."""
    if raw:
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return {agent_id: dict(config) for agent_id, config in contract.DEFAULT_AGENT_CONFIGS.items()}


def orchestrator_models(configs: dict[str, dict]) -> dict:
    """로이드가 읽을 파일 내용(실행.md §3). 호출에 그대로 넣을 값만 둔다."""
    yor = configs.get("yor") or contract.DEFAULT_AGENT_CONFIGS["yor"]
    return {
        "yor": {"model": yor["modelId"], "effort": yor["reasoningLevel"]},
        "yuri": {"model": SUBAGENT_ALIAS.get((configs.get("yuri") or {}).get("modelId", ""), "sonnet")},
        "anya": {"model": SUBAGENT_ALIAS.get((configs.get("anya") or {}).get("modelId", ""), "opus")},
    }


# --- 실행 뒤 대조: 로이드가 실제로 넘긴 값이 설정과 같은지 -------------------------------

_CODEX_MODEL = re.compile(r"codex(?:\.cmd)?\s+exec\b.*?\s-m\s+\"?([\w.\-]+)")
_CODEX_EFFORT = re.compile(r"model_reasoning_effort=\"?([\w\-]+)")


def check_model_calls(log_path: Path, expected: dict) -> list[str]:
    """stream-json 실행 기록의 도구 호출(Agent·Bash/PowerShell의 codex)을 보고, 설정과 다른 호출을 문장으로 돌려준다."""
    problems: list[str] = []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return problems
    subagent_models = {expected["yuri"]["model"], expected["anya"]["model"]}
    for line in lines:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        content = (message.get("message") or {}).get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            data = block.get("input") or {}
            if block.get("name") == "Agent" and data.get("model") and data["model"] not in subagent_models:
                problems.append(f"서브에이전트를 설정에 없는 모델({data['model']})로 불렀습니다.")
            command = str(data.get("command") or "")
            if "codex" in command and " exec" in command:
                model = _CODEX_MODEL.search(command)
                effort = _CODEX_EFFORT.search(command)
                if not model or model[1] != expected["yor"]["model"]:
                    problems.append(f"요르(codex)를 설정과 다른 모델({model[1] if model else '미지정'})로 불렀습니다.")
                if not effort or effort[1] != expected["yor"]["effort"]:
                    problems.append(f"요르(codex)를 설정과 다른 추론 강도({effort[1] if effort else '미지정'})로 불렀습니다.")
    return list(dict.fromkeys(problems))
