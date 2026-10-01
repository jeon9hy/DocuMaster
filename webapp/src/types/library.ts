import type { ProjectMode } from "./project";

/** 라이브러리 한 줄 = 최종본이 있는 작업 하나. 파일에서 읽은 값만 담는다(server/app/library.py). */
export interface LibraryDocument {
  projectId: string;
  workspaceId: string;
  title: string;
  /** 00의 원문 요청. 없으면 빈 문자열 */
  request: string;
  /** `최종/<유형>/` 폴더 이름(가운뎃점 없음). 예: 설명해설 · 발표 */
  kind: string;
  mode: ProjectMode;
  /** YYYY-MM-DD. 작업 ID 끝의 날짜 */
  date: string;
  /** 대표 파일 이름(PDF 우선). 없으면 null */
  fileName: string | null;
  /** 대표 파일의 작업물 ID. 아직 등록 전이면 null — 그때는 프로젝트 작업물 화면만 연다 */
  artifactId: string | null;
}

/** 드롭다운에서 고르는 필터 종류 */
export type LibraryFilterField = "title" | "date" | "kind";

export interface LibraryFilter {
  title: string;
  /** YYYY-MM-DD. 빈 문자열이면 제한 없음 */
  dateFrom: string;
  dateTo: string;
  /** 비어 있으면 전체 */
  kinds: string[];
}
