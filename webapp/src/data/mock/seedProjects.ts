import type {
  AgentId,
  Artifact,
  ArtifactContent,
  ProjectSummary,
  WorkflowEventPayload,
  WorkflowStageId,
} from "@/types";

/**
 * 처음 화면에 보일 목업 프로젝트.
 * 상태를 직접 적지 않고 "지금까지 일어난 이벤트"로 적는다 — 서비스가 이 이벤트를 재생해
 * 화면 상태를 만들기 때문에, 실제 실행 때와 똑같은 규칙으로 피드·진행률이 채워진다.
 */
export interface SeedEvent {
  minutesAgo: number;
  payload: WorkflowEventPayload;
}

export interface ProjectSeed {
  summary: ProjectSummary;
  events: SeedEvent[];
  contents: Record<string, ArtifactContent>;
}

type SeedArtifact = Omit<Artifact, "updatedAt">;

const at = (minutesAgo: number, payload: WorkflowEventPayload): SeedEvent => ({
  minutesAgo,
  payload,
});

/** 한 에이전트가 한 단계를 끝까지 마친 기록 */
function completedStage(
  minutesAgo: number,
  stageId: WorkflowStageId,
  agentId: AgentId,
  message: string,
  artifact: SeedArtifact,
): SeedEvent[] {
  return [
    at(minutesAgo, { type: "workflow.stage.started", stageId }),
    at(minutesAgo, { type: "agent.started", agentId, stageId }),
    at(minutesAgo - 3, { type: "agent.message", agentId, text: message }),
    at(minutesAgo - 4, { type: "artifact.created", artifact }),
    at(minutesAgo - 4, { type: "agent.completed", agentId }),
    at(minutesAgo - 4, { type: "workflow.stage.completed", stageId }),
  ];
}

function pendingArtifacts(minutesAgo: number, artifacts: SeedArtifact[]): SeedEvent[] {
  return artifacts.map((artifact) => at(minutesAgo, { type: "artifact.created", artifact }));
}

const markdown = (text: string): ArtifactContent => ({ type: "markdown", text: text.trim() });

const housing: ProjectSeed = {
  summary: {
    id: "housing-2026",
    name: "2026 주거 정책 보고서",
    description: "주거 안정화 방안에 대한 종합 연구",
    mode: "document",
  },
  events: [
    at(1500, {
      type: "reference.added",
      reference: {
        id: "housing-ref-seoul",
        name: "서울시_주거_현황.png",
        kind: "image",
        detail: "이미지 · 2.1MB",
        applyPolicy: "nextStage",
      },
    }),
    at(95, {
      type: "reference.added",
      reference: {
        id: "housing-ref-stat",
        name: "주거정책 통계 데이터",
        kind: "url",
        detail: "웹 링크 · stat.molit.go.kr",
        applyPolicy: "nextStage",
      },
    }),
    at(90, {
      type: "user.message",
      text: "2026 주거 정책 보고서를 제출용 문서로 만들어 주세요. 독자는 정책 담당자, 분량은 15쪽 안팎입니다.",
    }),
    at(89, { type: "workflow.started" }),
    ...completedStage(
      89,
      "requirements",
      "loid",
      "문서(DOCUMENT) 모드로 판정했습니다. 독자·분량·형식과 가정을 00에 정리했습니다.",
      {
        id: "housing-00",
        name: "00_user_brief.md",
        fileType: "markdown",
        status: "latest",
        stageId: "requirements",
        agentId: "loid",
        summary: "주제·독자·분량·형식 정리",
      },
    ),
    ...completedStage(
      84,
      "planning",
      "loid",
      "핵심 메시지는 ① 현황 진단 → ② 정책 제안 → ③ 기대 효과 흐름입니다. 7장 구성으로 기획 게이트를 통과했습니다.",
      {
        id: "housing-01",
        name: "01_plan.md",
        fileType: "markdown",
        status: "latest",
        stageId: "planning",
        agentId: "loid",
        summary: "7장 구성 · 기획 게이트 통과",
      },
    ),
    at(79, { type: "handoff.created", fromAgentId: "loid", toAgentId: "yor", artifactName: "01_plan.md" }),
    at(79, { type: "workflow.stage.started", stageId: "research" }),
    at(79, { type: "agent.started", agentId: "yor", stageId: "research" }),
    ...pendingArtifacts(78, [
      {
        id: "housing-02",
        name: "02_research.md",
        fileType: "markdown",
        status: "writing",
        stageId: "research",
        agentId: "yor",
        summary: "근거 목록과 출처",
      },
      {
        id: "housing-05",
        name: "05_validation.md",
        fileType: "markdown",
        status: "pending",
        stageId: "validation",
        agentId: "yuri",
        summary: "검증 판정",
      },
      {
        id: "housing-07",
        name: "07_document.md",
        fileType: "markdown",
        status: "pending",
        stageId: "writing",
        agentId: "anya",
        summary: "최종 문서 원고",
      },
      {
        id: "housing-final",
        name: "final.pdf",
        fileType: "pdf",
        status: "pending",
        stageId: "finalReview",
        agentId: "loid",
        summary: "제출용 최종본",
      },
    ]),
    at(66, {
      type: "agent.message",
      agentId: "yor",
      text: "관련 자료 14건을 모았습니다. 정부 통계와 논문 원문을 직접 열어 확인한 것만 근거로 적고 있습니다.",
    }),
    at(58, {
      type: "artifact.created",
      artifact: {
        id: "housing-chart",
        name: "02_rent_trend_chart.svg",
        fileType: "image",
        status: "latest",
        stageId: "research",
        agentId: "yor",
        summary: "주거비 추이 예시 차트",
      },
    }),
    at(40, {
      type: "reference.added",
      reference: {
        id: "housing-ref-molit",
        name: "국토교통부_2026_보고서.pdf",
        kind: "pdf",
        detail: "PDF · 12.4MB",
        applyPolicy: "nextStage",
      },
    }),
    at(38, {
      type: "agent.message",
      agentId: "yor",
      text: "추가된 보고서는 다음 단계부터 반영하겠습니다. 지금은 2020~2025년 주거비 추이 자료를 정리하는 중입니다.",
    }),
  ],
  contents: {
    "housing-00": markdown(`
# 00 사용자 요청 정리
- 주제: 2026 주거 정책 보고서
- 모드: DOCUMENT (제출용 최종본)
- 독자: 정책 담당자
- 분량: 15쪽 안팎
## 가정
- 기준 시점은 작성일, 통계는 가장 최근 확정치를 씁니다.
`),
    "housing-01": markdown(`
# 01 기획안
## 핵심 메시지
① 현황 진단 → ② 정책 제안 → ③ 기대 효과
## 목차 (7장)
1. 요약
2. 주거비 부담 현황
3. 공급 구조
4. 기존 정책 평가
5. 정책 제안
6. 기대 효과와 한계
7. 결론
`),
    "housing-02": markdown(`
# 02 조사 결과 (작성 중)
## 확인한 근거
- 주거비 추이 — 국가 통계 원문 확인
- 공급 물량 — 부처 보도자료 원문 확인
## 확인 중
- 지역별 전월세 전환율 [미확인]
`),
    "housing-chart": {
      type: "image",
      src: "/mock/rent-trend-chart.svg",
      alt: "주거비 추이 예시 차트(목업)",
    },
  },
};

const chiikawa: ProjectSeed = {
  summary: {
    id: "chiikawa-deck",
    name: "치이카와 세계관 발표",
    description: "세계관과 캐릭터 관계를 소개하는 10분 발표",
    mode: "presentation",
  },
  events: [
    at(2900, {
      type: "user.message",
      text: "치이카와 세계관을 처음 보는 사람도 이해할 수 있게 10분 발표자료를 만들어 주세요.",
    }),
    at(2899, { type: "workflow.started" }),
    ...completedStage(
      2899,
      "requirements",
      "loid",
      "발표(PRESENTATION) 모드로 판정했습니다. 덱 유형은 스토리형입니다.",
      {
        id: "chiikawa-00",
        name: "00_user_brief.md",
        fileType: "markdown",
        status: "latest",
        stageId: "requirements",
        agentId: "loid",
        summary: "10분 발표 · 스토리형",
      },
    ),
    ...completedStage(2880, "planning", "loid", "8장 흐름으로 기획했습니다.", {
      id: "chiikawa-01",
      name: "01_plan.md",
      fileType: "markdown",
      status: "latest",
      stageId: "planning",
      agentId: "loid",
      summary: "8장 흐름",
    }),
    ...completedStage(
      2860,
      "research",
      "yor",
      "공식 설정과 팬 해석을 나눠 정리했습니다. 공식 출처가 없는 설정은 [미확인]으로 표시했습니다.",
      {
        id: "chiikawa-02",
        name: "02_research.md",
        fileType: "markdown",
        status: "latest",
        stageId: "research",
        agentId: "yor",
        summary: "공식 설정 · 팬 해석 구분",
      },
    ),
    at(2855, {
      type: "handoff.created",
      fromAgentId: "yor",
      toAgentId: "yuri",
      artifactName: "02_research.md",
    }),
    at(2855, { type: "workflow.stage.started", stageId: "validation" }),
    at(2855, { type: "agent.started", agentId: "yuri", stageId: "validation" }),
    ...pendingArtifacts(2854, [
      {
        id: "chiikawa-05",
        name: "05_validation.md",
        fileType: "markdown",
        status: "pending",
        stageId: "validation",
        agentId: "yuri",
        summary: "검증 판정",
      },
      {
        id: "chiikawa-07",
        name: "07_presentation_pack.md",
        fileType: "markdown",
        status: "pending",
        stageId: "writing",
        agentId: "yor",
        summary: "발표팩",
      },
    ]),
    at(2850, {
      type: "agent.message",
      agentId: "yuri",
      text: "캐릭터 관계 설정 중 공식 출처가 약한 3개를 골라 원문을 다시 확인하겠습니다.",
    }),
  ],
  contents: {
    "chiikawa-00": markdown(`
# 00 사용자 요청 정리
- 모드: PRESENTATION
- 덱 유형: 스토리형
- 분량: 10분 · 8장 안팎
`),
    "chiikawa-01": markdown(`
# 01 기획안
1. 표지
2. 세계관 한 줄 요약
3. 주요 캐릭터
4. 관계도
5. 반복되는 이야기 구조
6. 인기 요인
7. 정리
8. Q&A
`),
    "chiikawa-02": markdown(`
# 02 조사 결과
## 공식 설정
- 원작 연재처와 단행본 기준
## 팬 해석
- 공식 출처 없음 → 본문에서 해석임을 밝힐 것
`),
  },
};

const water: ProjectSeed = {
  summary: {
    id: "water-report",
    name: "수환경공학 보고서",
    description: "하천 수질 관리 사례 분석",
    mode: "document",
  },
  events: [],
  contents: {},
};

export const PROJECT_SEEDS: readonly ProjectSeed[] = [housing, chiikawa, water];
