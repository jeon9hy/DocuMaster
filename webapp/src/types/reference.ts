export type ReferenceKind = "pdf" | "image" | "url" | "text" | "markdown" | "file";

/** 작업 중 추가된 레퍼런스를 언제 반영할지. 기본값은 재실행 비용이 없는 nextStage. */
export type ReferenceApplyPolicy = "nextStage" | "currentAgent" | "rerunStage";

/** 파일 레퍼런스의 처리 상태. 백엔드가 저장·해시 계산을 마치면 ready. */
export type ReferenceParseStatus = "uploaded" | "processing" | "ready" | "error";

export interface Reference {
  id: string;
  name: string;
  kind: ReferenceKind;
  /** "PDF · 12.4MB", "mltm.go.kr" 같은 보조 표기 */
  detail: string;
  addedAt: string;
  applyPolicy: ReferenceApplyPolicy;
  /** 없으면 ready로 본다(목업·URL·텍스트) */
  parseStatus?: ReferenceParseStatus;
}

export type NewReferenceInput = { applyPolicy: ReferenceApplyPolicy } & (
  /** file은 실제 업로드용 File 객체. 목업은 이름·크기만 쓴다. */
  | { source: "file"; file: File }
  | { source: "url"; url: string; title: string }
  | { source: "text"; title: string; text: string }
);
