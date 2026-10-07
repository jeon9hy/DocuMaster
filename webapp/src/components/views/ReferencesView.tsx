"use client";

import { useState } from "react";
import { Plus, Upload } from "lucide-react";
import { DEFAULT_APPLY_POLICY } from "@/constants/references";
import { useReferenceFileUpload } from "@/hooks/useReferenceFileUpload";
import { useAppActions, useIsOwner, useWorkspace } from "@/state/WorkspaceProvider";
import type { ReferenceApplyPolicy } from "@/types";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { ApplyPolicyField } from "../reference/ApplyPolicyField";
import { FileDropZone } from "../reference/FileDropZone";
import { ReferenceList } from "../reference/ReferenceList";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 실행 중일 때만 반영 시점이 의미가 있다 — 멈춰 있으면 다음 실행 첫 턴에 함께 넘어간다 */
const ACTIVE_RUN = ["running", "awaitingInput", "stopping"];

/** 파일 여러 개를 끌어다 놓아 담고 한 번에 올린다 */
function FileUploadPanel() {
  const workspace = useWorkspace();
  const { upload, progress, uploading } = useReferenceFileUpload();
  const [files, setFiles] = useState<File[]>([]);
  const [applyPolicy, setApplyPolicy] = useState<ReferenceApplyPolicy>(DEFAULT_APPLY_POLICY);
  const [error, setError] = useState<string | null>(null);
  const running = ACTIVE_RUN.includes(workspace.runStatus);

  const submit = async () => {
    setError(null);
    const result = await upload(files, applyPolicy);
    setFiles(result.failed);
    if (result.failed.length) setError(`${result.failed.length}개를 올리지 못했습니다: ${result.error}`);
  };

  return (
    <Panel
      title="파일 올리기"
      action={
        <AddReferenceButton>
          {(open) => (
            <Button size="sm" variant="ghost" icon={Plus} onClick={open} className="h-7 text-blue-600">
              URL·텍스트
            </Button>
          )}
        </AddReferenceButton>
      }
      bodyClassName="space-y-4"
    >
      <FileDropZone files={files} onChange={setFiles} disabled={uploading} />
      {running && files.length > 0 && <ApplyPolicyField value={applyPolicy} onChange={setApplyPolicy} />}
      {(files.length > 0 || error) && (
        <div className="flex flex-wrap items-center justify-end gap-3">
          {error && <p className="mr-auto text-sm text-red-600">{error}</p>}
          {files.length > 0 && !uploading && (
            <Button size="sm" onClick={() => setFiles([])}>
              모두 비우기
            </Button>
          )}
          {files.length > 0 && (
            <Button size="sm" variant="primary" icon={Upload} onClick={submit} disabled={uploading}>
              {progress ? `올리는 중… ${progress.done}/${progress.total}` : `${files.length}개 올리기`}
            </Button>
          )}
        </div>
      )}
    </Panel>
  );
}

/** 프로젝트 레퍼런스 전체 — 여러 파일 업로드 + 목록·삭제. 모바일 「레퍼런스」 탭에서도 쓴다. */
export function ReferencesView() {
  const workspace = useWorkspace();
  const { removeReference } = useAppActions();
  const canEdit = useIsOwner() && !workspace.project.readOnly;

  return (
    <ViewContainer>
      <ViewHeader title="레퍼런스" description="이 프로젝트에서 참고할 자료입니다. 프로젝트를 처음 실행할 때 이 목록이 로이드에게 넘어갑니다." />
      <div className="space-y-4">
        {canEdit && <FileUploadPanel />}
        <Panel title={`자료 (${workspace.references.length})`}>
          <ReferenceList references={workspace.references} onRemove={canEdit ? removeReference : undefined} />
        </Panel>
      </div>
    </ViewContainer>
  );
}
