/** 로고 이미지 경로. 파일은 public/brand/에 둔다(public/brand/README.md 참고). */
export const BRAND = {
  name: "DocuMaster",
  /** 브라우저 메타 설명용. 헤더에는 보이지 않는다(로고는 마크 + 워드마크만). */
  description: "조사 기반 문서·발표 오케스트레이션",
  markSrc: "/brand/logo-mark.svg",
  /** 워드마크 이미지. 비워 두면 BrandLogo가 "docu"(파랑) + "master"(남색) 글자로 그린다. */
  wordmarkSrc: undefined as string | undefined,
} as const;
