export type ReferenceKind = "pdf" | "image" | "url" | "text" | "markdown" | "file";

/** 작업 중 추가된 레퍼런스를 언제 반영할지. 기본값은 재실행 비용이 없는 nextStage. */
export type ReferenceApplyPolicy = "nextStage" | "currentAgent" | "rerunStage";

export interface Reference {
  id: string;
  name: string;
  kind: ReferenceKind;
  /** "PDF · 12.4MB", "mltm.go.kr" 같은 보조 표기 */
  detail: string;
  addedAt: string;
  applyPolicy: ReferenceApplyPolicy;
}

export type NewReferenceInput = { applyPolicy: ReferenceApplyPolicy } & (
  | { source: "file"; fileName: string; sizeBytes: number }
  | { source: "url"; url: string; title: string }
  | { source: "text"; title: string; text: string }
);
