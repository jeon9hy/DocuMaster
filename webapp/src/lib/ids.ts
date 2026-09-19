let counter = 0;

/** 목업·로컬 상태용 ID. 실제 백엔드가 생기면 서버가 준 ID를 그대로 쓴다. */
export function createId(prefix: string): string {
  counter += 1;
  return `${prefix}_${Date.now().toString(36)}_${counter}`;
}
