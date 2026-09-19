import { useEffect, useState } from "react";
import { workspaceService } from "@/services";
import type { Artifact, ArtifactContent } from "@/types";

export type ContentResult =
  | { status: "loading" }
  | { status: "success"; content: ArtifactContent }
  | { status: "empty" }
  | { status: "error"; message: string };

// 같은 버전(updatedAt)의 본문은 한 번만 불러온다. 작업물이 갱신되면 키가 바뀌어 다시 부른다.
const cache = new Map<string, ArtifactContent>();

/** 미리보기를 열 때만 본문을 불러온다(목록 단계에서는 메타데이터만). */
export function useArtifactContent(projectId: string, artifact: Artifact | null): ContentResult {
  const artifactId = artifact?.id;
  const hasContent = artifact !== null && artifact.status !== "pending";
  const key = artifact ? `${projectId}:${artifact.id}:${artifact.updatedAt}` : "";
  const [loaded, setLoaded] = useState<{ key: string; result: ContentResult } | null>(null);

  useEffect(() => {
    if (!artifactId || !hasContent || cache.has(key)) return;
    let cancelled = false;
    workspaceService
      .getArtifactContent(projectId, artifactId)
      .then((content) => {
        // 본문이 아직 없으면(작성 중) 캐시하지 않는다 — 완성되면 updatedAt이 바뀌어 다시 부른다.
        if (content) cache.set(key, content);
        if (cancelled) return;
        setLoaded({ key, result: content ? { status: "success", content } : { status: "empty" } });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "미리보기를 불러오지 못했습니다.";
        if (!cancelled) setLoaded({ key, result: { status: "error", message } });
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, artifactId, hasContent, key]);

  if (!hasContent) return { status: "empty" };
  const cached = cache.get(key);
  if (cached) return { status: "success", content: cached };
  return loaded?.key === key ? loaded.result : { status: "loading" };
}
