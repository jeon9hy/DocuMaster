/**
 * 로이드 → 하위 에이전트 전달문(SendMessage 원문)을 대화용 한 줄로 줄인다. 코드가 만드는 문구다.
 * 원문 형식은 루트 `.claude/로이드/실행.md`(「이번 호출: 05. 입력: …」)와 `skills/doc-finish`(「REVISE: …」)가 정한다.
 */
const CALL_LABEL: Record<string, string> = {
  "03": "검증 질문 요청",
  "05": "검증 판정 요청",
  "07": "문서 작성 요청",
};

export function summarizeHandoff(text: string): string {
  const call = /이번 호출:\s*(\d{2})/.exec(text)?.[1];
  if (call) return CALL_LABEL[call] ?? `${call} 작업 요청`;
  if (/^\s*REVISE\b/.test(text)) return "수정 요청";
  return "작업 전달";
}
