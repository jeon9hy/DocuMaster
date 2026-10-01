import type { LibraryDocument } from "@/types";

/** 백엔드 없이 화면만 볼 때의 라이브러리. projectId는 seedProjects.ts의 프로젝트를 가리킨다. */
export const LIBRARY_SEEDS: readonly LibraryDocument[] = [
  {
    projectId: "housing-2026",
    workspaceId: "주거정책보고서_20261001",
    title: "2026 주거 정책 보고서",
    request: "청년 주거 안정화 정책을 분석한 보고서를 만들어줘",
    kind: "분석",
    mode: "document",
    date: "2026-10-01",
    fileName: "주거정책보고서_20261001.pdf",
    artifactId: "housing-final",
  },
  {
    projectId: "water-report",
    workspaceId: "수환경공학보고서_20260924",
    title: "수환경공학 보고서",
    request: "하천 수질 관리 사례를 정리해줘",
    kind: "현황기록",
    mode: "document",
    date: "2026-09-24",
    fileName: "수환경공학보고서_20260924.pdf",
    artifactId: null,
  },
  {
    projectId: "chiikawa-deck",
    workspaceId: "치이카와세계관_20260918",
    title: "치이카와 세계관 발표",
    request: "치이카와 세계관을 소개하는 10분 발표 자료",
    kind: "발표",
    mode: "presentation",
    date: "2026-09-18",
    fileName: "치이카와세계관_20260918_슬라이드.pdf",
    artifactId: null,
  },
];
