import { REFERENCE_KIND_LABEL } from "@/constants/references";
import type { NewReferenceInput, Reference, ReferenceKind } from "@/types";
import { formatBytes } from "./format";

const KIND_BY_EXTENSION: Record<string, ReferenceKind> = {
  pdf: "pdf",
  png: "image",
  jpg: "image",
  jpeg: "image",
  gif: "image",
  webp: "image",
  md: "markdown",
  txt: "text",
};

function kindFromFileName(fileName: string): ReferenceKind {
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  return KIND_BY_EXTENSION[extension] ?? "file";
}

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/** 사용자 입력을 레퍼런스 한 건으로 만든다. 파일 내용은 읽지 않는다(목업 단계). */
export function buildReference(input: NewReferenceInput, id: string): Omit<Reference, "addedAt"> {
  const base = { id, applyPolicy: input.applyPolicy };
  switch (input.source) {
    case "file": {
      const kind = kindFromFileName(input.fileName);
      return {
        ...base,
        kind,
        name: input.fileName,
        detail: `${REFERENCE_KIND_LABEL[kind]} · ${formatBytes(input.sizeBytes)}`,
      };
    }
    case "url":
      return {
        ...base,
        kind: "url",
        name: input.title || hostnameOf(input.url),
        detail: `${REFERENCE_KIND_LABEL.url} · ${hostnameOf(input.url)}`,
      };
    case "text":
      return {
        ...base,
        kind: "text",
        name: input.title,
        detail: `${REFERENCE_KIND_LABEL.text} · ${input.text.length.toLocaleString()}자`,
      };
  }
}
