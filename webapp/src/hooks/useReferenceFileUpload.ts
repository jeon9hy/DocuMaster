import { useCallback, useState } from "react";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { ReferenceApplyPolicy } from "@/types";

export interface UploadProgress {
  done: number;
  total: number;
}

export interface UploadResult {
  /** 올리지 못한 파일 — 화면에 남겨 다시 시도하게 한다 */
  failed: File[];
  /** 첫 실패의 사유 */
  error: string | null;
}

/**
 * 여러 파일을 레퍼런스로 올린다. 서버는 한 요청에 한 파일을 받으므로 차례로 보낸다
 * (동시에 보내면 같은 이름 처리·이벤트 순서가 섞인다). 하나가 실패해도 나머지는 계속 올린다.
 */
export function useReferenceFileUpload() {
  const { addReference } = useAppActions();
  const [progress, setProgress] = useState<UploadProgress | null>(null);

  const upload = useCallback(
    async (files: File[], applyPolicy: ReferenceApplyPolicy): Promise<UploadResult> => {
      const failed: File[] = [];
      let error: string | null = null;
      setProgress({ done: 0, total: files.length });
      for (const [index, file] of files.entries()) {
        try {
          await addReference({ source: "file", applyPolicy, file });
        } catch (caught) {
          failed.push(file);
          error ??= caught instanceof Error ? caught.message : "업로드하지 못했습니다.";
        }
        setProgress({ done: index + 1, total: files.length });
      }
      setProgress(null);
      return { failed, error };
    },
    [addReference],
  );

  return { upload, progress, uploading: progress !== null };
}
