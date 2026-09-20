import { AGENT_PROFILES } from "@/constants/agents";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { APPLY_POLICY_LABEL } from "@/constants/references";
import { STAGE_BY_ID } from "@/constants/workflow";
import type { FeedItem, ProjectWorkspace, WorkflowEvent } from "@/types";
import { describeModelConfig } from "./models";

const VERDICT_TONE = { passed: "success", conditional: "warning", blocked: "error" } as const;

/**
 * 이벤트 → 피드 한 줄. 진행·완료·전달 같은 문구는 전부 여기서 코드로 만든다(LLM 호출 없음).
 * 피드에 남길 필요가 없는 이벤트는 null. 내부 전달·파일 갱신처럼 자주 생기는 줄은
 * importance: "detail"로 표시해 피드에서 접어 보여 준다.
 */
export function eventToFeedItem(
  event: WorkflowEvent,
  workspace: ProjectWorkspace,
): FeedItem | null {
  const base = { id: event.id, createdAt: event.at };
  const name = (id: keyof typeof AGENT_PROFILES) => AGENT_PROFILES[id].name;

  switch (event.type) {
    case "user.message":
      return { ...base, kind: "user", text: event.text };

    case "agent.message":
      return { ...base, kind: "agent", agentId: event.agentId, toAgentId: event.toAgentId, text: event.text };

    case "agent.activity":
      return { ...base, kind: "activity", agentId: event.agentId, label: event.label };

    case "workflow.started":
      return { ...base, kind: "system", tone: "info", title: "워크플로우 실행 시작" };

    case "workflow.stage.started":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 시작`,
      };

    case "workflow.stage.completed":
      return {
        ...base,
        kind: "system",
        tone: "success",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 완료`,
      };

    case "workflow.warning":
      return {
        ...base,
        kind: "system",
        tone: "warning",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 확인 필요`,
        detail: event.message,
      };

    case "workflow.completed":
      return {
        ...base,
        kind: "system",
        tone: "success",
        title: "워크플로우 완료",
        detail: "최종본이 작업물에 추가되었습니다.",
      };

    case "workflow.stop.requested":
      return {
        ...base,
        kind: "system",
        tone: "warning",
        title: "중지 요청됨",
        detail: "현재 단계가 끝나면 멈춥니다.",
      };

    case "workflow.stopped":
      return {
        ...base,
        kind: "system",
        tone: "warning",
        title: "실행 중지",
        detail: `다시 실행하면 ${STAGE_BY_ID[event.stageId].label} 단계부터 이어서 합니다.`,
      };

    case "project.mode.decided":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: `모드 판정: ${PROJECT_MODE_LABEL[event.mode]}`,
      };

    case "validation.verdict": {
      // 과거 로그에는 05를 같은 판정으로 다시 저장할 때 중복 이벤트가 남아 있다.
      const lastVerdict = workspace.feed.findLast(
        (item) => item.kind === "system" && item.title.startsWith("05 검증 결과:"),
      );
      if (lastVerdict?.kind === "system" && lastVerdict.title === `05 검증 결과: ${event.verdict}`)
        return null;
      return {
        ...base,
        kind: "system",
        tone: VERDICT_TONE[event.verdict],
        title: `05 검증 결과: ${event.verdict}`,
        detail: event.firstLine,
      };
    }

    case "user.input.required":
      return { ...base, kind: "input", request: event.request };

    case "user.input.resolved":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: "사용자 응답 전달",
        detail: event.answer,
      };

    case "workflow.failed":
      return {
        ...base,
        kind: "system",
        tone: "error",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 실패`,
        detail: event.reason,
      };

    case "agent.started":
      return {
        ...base,
        kind: "system",
        tone: "info",
        agentId: event.agentId,
        title: `${name(event.agentId)} · ${STAGE_BY_ID[event.stageId].label} 작업 시작`,
      };

    case "agent.configured":
      return {
        ...base,
        kind: "system",
        tone: "info",
        agentId: event.agentId,
        title: `${name(event.agentId)} 모델 변경`,
        detail: describeModelConfig(event.config),
        importance: "detail",
      };

    case "handoff.created":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: `${name(event.fromAgentId)} → ${name(event.toAgentId)} 전달 완료`,
        detail: event.artifactName,
      };

    case "reference.added":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: "새 레퍼런스 추가됨",
        detail: `${event.reference.name} · ${APPLY_POLICY_LABEL[event.reference.applyPolicy]}`,
      };

    case "reference.removed":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: "레퍼런스 삭제됨",
        importance: "detail",
      };

    // 같은 파일을 퇴고하며 여러 번 저장해도 카드는 한 장이다. 내용·표시는 artifact 상태에서 갱신된다.
    case "artifact.updated":
      return null;

    // 내부 작업물(03·04·06 등)은 접는다.
    case "artifact.created":
    {
      const artifactId = event.artifact.id;
      const artifact = workspace.artifacts.find((item) => item.id === artifactId);
      if (!artifact || artifact.status !== "latest") return null;
      return {
        ...base,
        kind: "artifact",
        artifactId: artifact.id,
        agentId: artifact.agentId,
        ...(artifact.visibility === "internal" && { importance: "detail" as const }),
      };
    }

    case "agent.completed":
      return null;
  }
}
