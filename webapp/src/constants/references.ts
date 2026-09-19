import type { ReferenceApplyPolicy, ReferenceKind } from "@/types";

export const REFERENCE_KIND_LABEL: Record<ReferenceKind, string> = {
  pdf: "PDF",
  image: "이미지",
  url: "웹 링크",
  text: "텍스트",
  markdown: "Markdown",
  file: "파일",
};

export const APPLY_POLICIES: readonly {
  id: ReferenceApplyPolicy;
  label: string;
  hint: string;
}[] = [
  {
    id: "nextStage",
    label: "다음 단계부터 반영",
    hint: "진행 중인 작업을 다시 돌리지 않습니다. 토큰이 가장 적게 듭니다.",
  },
  {
    id: "currentAgent",
    label: "현재 에이전트에게 전달",
    hint: "지금 작업 중인 에이전트가 이 자료를 추가로 받습니다.",
  },
  {
    id: "rerunStage",
    label: "관련 단계부터 다시 실행",
    hint: "이 자료를 읽는 단계부터 다시 돌립니다. 비용이 가장 큽니다.",
  },
];

export const DEFAULT_APPLY_POLICY: ReferenceApplyPolicy = "nextStage";

export const APPLY_POLICY_LABEL = Object.fromEntries(
  APPLY_POLICIES.map((policy) => [policy.id, policy.label]),
) as Record<ReferenceApplyPolicy, string>;
