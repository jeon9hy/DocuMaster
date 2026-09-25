import type {
  AgentId,
  ArtifactContent,
  ArtifactFileType,
  ArtifactVisibility,
  ProjectMode,
  ValidationVerdict,
  WorkflowStageId,
} from "@/types";

/**
 * 목업 실행 대본. 「실행」을 누르면 services/mock/buildRunPlan.ts가 이 대본을
 * 이벤트로 바꿔 순서대로 내보낸다. 문구를 바꾸려면 이 파일만 고치면 된다.
 */
export type ScriptStep =
  | { kind: "start"; agentId: AgentId }
  | { kind: "say"; agentId: AgentId; text: string }
  | {
      kind: "artifact";
      agentId: AgentId;
      name: string;
      fileType: ArtifactFileType;
      summary: string;
      content: ArtifactContent;
      visibility?: ArtifactVisibility;
    }
  | { kind: "handoff"; from: AgentId; to: AgentId; artifactName?: string }
  | { kind: "warning"; message: string }
  | { kind: "verdict"; verdict: ValidationVerdict; firstLine: string }
  /** 여기서 실행을 멈추고 사용자 응답을 기다린다. 응답하면 다음 단계부터 이어진다. */
  | { kind: "ask"; title: string; message: string; choices: string[] }
  | { kind: "done"; agentId: AgentId };

type StageScripts = Record<WorkflowStageId, readonly ScriptStep[]>;

const markdown = (text: string): ArtifactContent => ({ type: "markdown", text: text.trim() });

const COMMON: Omit<StageScripts, "writing" | "finalReview"> = {
  requirements: [
    { kind: "start", agentId: "loid" },
    {
      kind: "say",
      agentId: "loid",
      text: "요청을 읽고 주제·독자·분량·형식을 정리했습니다. 애매한 부분은 가정으로 적어 두었습니다.",
    },
    {
      kind: "artifact",
      agentId: "loid",
      name: "00_user_brief.md",
      fileType: "markdown",
      summary: "주제·독자·분량·형식 정리",
      content: markdown(`
# 00 사용자 요청 정리
- 주제: 사용자가 입력한 주제
- 독자: 의사결정권자
- 분량: 15쪽 안팎
- 형식: PDF 제출본
## 가정
- 기준 시점은 작성일로 둡니다.
`),
    },
    { kind: "done", agentId: "loid" },
  ],
  planning: [
    { kind: "start", agentId: "loid" },
    {
      kind: "say",
      agentId: "loid",
      text: "핵심 질문 3개와 목차를 세웠습니다. 기획 게이트를 통과했습니다.",
    },
    {
      kind: "artifact",
      agentId: "loid",
      name: "01_plan.md",
      fileType: "markdown",
      summary: "핵심 질문과 목차",
      content: markdown(`
# 01 기획안
## 핵심 질문
1. 현황은 어떤가?
2. 무엇이 원인인가?
3. 어떤 선택지가 있는가?
## 목차
- 요약
- 현황 진단
- 원인 분석
- 정책 선택지
- 결론
`),
    },
    { kind: "done", agentId: "loid" },
    { kind: "handoff", from: "loid", to: "yor", artifactName: "01_plan.md" },
  ],
  research: [
    { kind: "start", agentId: "yor" },
    {
      kind: "say",
      agentId: "yor",
      text: "기획안의 질문마다 원문을 직접 열어 근거를 모으고 있습니다. 열지 못한 자료는 [미확인]으로 남기겠습니다.",
    },
    {
      kind: "say",
      agentId: "yor",
      text: "출처끼리 값이 다른 항목은 두 값을 모두 적었습니다. 채택은 로이드에게 맡기겠습니다.",
    },
    {
      kind: "artifact",
      agentId: "yor",
      name: "02_research.md",
      fileType: "markdown",
      summary: "근거 목록과 출처",
      content: markdown(`
# 02 조사 결과
## 확인한 근거
- 주장 A — 출처 1 (원문 확인)
- 주장 B — 출처 2 (원문 확인)
## 값이 엇갈리는 항목
- 지표 C: 출처 3과 출처 4의 값이 다름 → 둘 다 기재
## 미확인
- 주장 D — 원문 접근 불가 [미확인]
`),
    },
    { kind: "done", agentId: "yor" },
    { kind: "handoff", from: "yor", to: "yuri", artifactName: "02_research.md" },
  ],
  validation: [
    { kind: "start", agentId: "yuri" },
    {
      kind: "say",
      agentId: "yuri",
      text: "위험한 주장 7개를 골라 질문을 보냈습니다. 수치의 기준 시점과 집계 범위를 특히 보겠습니다.",
    },
    {
      kind: "artifact",
      agentId: "yuri",
      name: "03_validation_questions.md",
      fileType: "markdown",
      summary: "검증 질문 7개",
      visibility: "internal",
      content: markdown(`
# 03 검증 질문
1. 주장 A의 기준 시점은?
2. 주장 B의 집계 범위는?
3. 주장 D를 대체할 근거가 있는가?
`),
    },
    { kind: "handoff", from: "yuri", to: "yor", artifactName: "03_validation_questions.md" },
    { kind: "start", agentId: "yor" },
    {
      kind: "say",
      agentId: "yor",
      text: "질문 7개에 답했습니다. 주장 D는 대체 근거를 찾지 못해 제외를 제안합니다.",
    },
    { kind: "done", agentId: "yor" },
    {
      kind: "warning",
      message: "REMOVE 1건 · CAUTION 2건 — CAUTION은 본문에 명시하고, REMOVE는 쓰지 않습니다.",
    },
    {
      kind: "artifact",
      agentId: "yuri",
      name: "05_validation.md",
      fileType: "markdown",
      summary: "검증 통과 — 조건부",
      content: markdown(`
# 05 검증 판정
검증 통과 — 조건부
## APPROVED
- 주장 A, 주장 B
## CAUTION
- 지표 C: 출처 간 값 차이를 본문에 함께 적을 것
## REMOVE
- 주장 D: 원문 미확인
`),
    },
    { kind: "done", agentId: "yuri" },
    { kind: "verdict", verdict: "conditional", firstLine: "검증 통과 — 조건부" },
    {
      kind: "ask",
      title: "조건부 판정 채택",
      message: "REMOVE 1건 · CAUTION 2건을 반영하고 최종 작성을 진행할까요?",
      choices: ["반영하고 계속", "작업 중단"],
    },
    {
      kind: "say",
      agentId: "loid",
      text: "05 판정을 채택합니다. 이후 단계는 05에 있는 사실만 씁니다.",
    },
  ],
};

const DETAILED_PLAN: readonly ScriptStep[] = [
  { kind: "start", agentId: "yor" },
  {
    kind: "artifact",
    agentId: "yor",
    name: "06_detailed_plan.md",
    fileType: "markdown",
    summary: "장별 구조 · LOCKED",
    visibility: "internal",
    content: markdown(`
# 06 세부 기획 (LOCKED)
## 1장 현황 진단
- 주장 A (APPROVED)
## 2장 원인 분석
- 주장 B (APPROVED)
- 지표 C (CAUTION 문구 포함)
`),
  },
];

const WRITING: Record<ProjectMode, readonly ScriptStep[]> = {
  document: [
    { kind: "handoff", from: "yuri", to: "anya", artifactName: "05_validation.md" },
    { kind: "start", agentId: "anya" },
    {
      kind: "say",
      agentId: "anya",
      text: "00의 목적과 05의 검증된 사실로 구조와 비주얼을 직접 정하고, CAUTION은 관련 주장 가까이에 반영할게요!",
    },
    {
      kind: "artifact",
      agentId: "anya",
      name: "07_document.md",
      fileType: "markdown",
      summary: "최종 문서 원고",
      content: markdown(`
# 최종 문서
## 요약
검증을 통과한 근거만으로 쓴 요약입니다.
## 1장 현황 진단
주장 A를 출처와 함께 서술합니다.
## 2장 원인 분석
지표 C는 출처마다 값이 달라 두 값을 함께 적습니다.
`),
    },
    { kind: "done", agentId: "anya" },
    { kind: "handoff", from: "anya", to: "loid", artifactName: "07_document.md" },
  ],
  presentation: [
    ...DETAILED_PLAN,
    {
      kind: "artifact",
      agentId: "yor",
      name: "07_presentation_pack.md",
      fileType: "markdown",
      summary: "발표팩 · 장별 화면 문구",
      content: markdown(`
# 07 발표팩
## 1장 표지
## 2장 왜 지금인가
## 3장 핵심 근거
## 4장 결론
`),
    },
    { kind: "done", agentId: "yor" },
    { kind: "handoff", from: "yor", to: "bond", artifactName: "07_presentation_pack.md" },
    { kind: "start", agentId: "bond" },
    { kind: "say", agentId: "bond", text: "왈! 발표팩과 원문만으로 슬라이드 초안을 만들었습니다." },
    {
      kind: "artifact",
      agentId: "bond",
      name: "slides_draft.pdf",
      fileType: "pdf",
      summary: "NotebookLM 슬라이드 초안",
      content: { type: "pdf", title: "슬라이드 초안", subtitle: "NotebookLM 생성본", pageCount: 12 },
    },
    { kind: "done", agentId: "bond" },
    { kind: "handoff", from: "bond", to: "loid", artifactName: "slides_draft.pdf" },
  ],
};

const FINAL_REVIEW: Record<ProjectMode, readonly ScriptStep[]> = {
  document: [
    { kind: "start", agentId: "loid" },
    {
      kind: "say",
      agentId: "loid",
      text: "크게 박힌 수치와 결론의 강도를 원문과 대조했습니다. 근거보다 센 문장은 없습니다.",
    },
    {
      kind: "artifact",
      agentId: "loid",
      name: "final.pdf",
      fileType: "pdf",
      summary: "제출용 최종본",
      content: { type: "pdf", title: "최종 보고서", subtitle: "검증 통과 — 조건부", pageCount: 15 },
    },
    { kind: "done", agentId: "loid" },
  ],
  presentation: [
    { kind: "start", agentId: "loid" },
    {
      kind: "say",
      agentId: "loid",
      text: "전 장을 모아 보고 의심 장만 확대해 확인했습니다. 화면 문구의 출처 표기를 맞췄습니다.",
    },
    {
      kind: "artifact",
      agentId: "loid",
      name: "final_slides.pdf",
      fileType: "pdf",
      summary: "슬라이드 초안 최종본",
      content: { type: "pdf", title: "발표 슬라이드", subtitle: "초안 · 디자인은 별도", pageCount: 12 },
    },
    { kind: "done", agentId: "loid" },
  ],
};

export const STAGE_SCRIPTS: Record<ProjectMode, StageScripts> = {
  document: { ...COMMON, writing: WRITING.document, finalReview: FINAL_REVIEW.document },
  presentation: { ...COMMON, writing: WRITING.presentation, finalReview: FINAL_REVIEW.presentation },
};

/** 사용자 지시에 대한 목업 답변 */
export const MOCK_REPLIES: Record<AgentId, string> = {
  loid: "지시를 확인했습니다. 기획 범위에 반영하고, 영향을 받는 단계를 상태 파일에 적어 두겠습니다.",
  yor: "확인했습니다. 원문을 열어 본 자료만 근거로 쓰고, 열지 못한 것은 [미확인]으로 표시하겠습니다.",
  yuri: "그 주장은 출처 원문과 직접 대조해 보겠습니다. 결과는 05 판정에 반영합니다.",
  anya: "알겠어요! 06 구조는 그대로 두고 문장 표현만 다듬을게요.",
  bond: "왈! 발표팩이 준비되면 바로 슬라이드 초안을 만들겠습니다.",
};
