"use client";

import { useCallback, useMemo, useState } from "react";
import { Library, SearchX } from "lucide-react";
import { DEFAULT_LIBRARY_FIELD, EMPTY_LIBRARY_FILTER } from "@/constants/library";
import { useServiceData } from "@/hooks/useServiceData";
import { countByKind, filterLibrary, groupByMonth } from "@/lib/library";
import { workspaceService } from "@/services";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { LibraryFilter, LibraryFilterField } from "@/types";
import { LibraryDocumentCard } from "../library/LibraryDocumentCard";
import { LibraryFilterBar } from "../library/LibraryFilterBar";
import { Button } from "../ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 최종본까지 끝난 문서를 날짜·제목·유형으로 찾아 연다. 목록은 화면을 열 때 한 번 받고 거르기는 화면에서 한다. */
export function LibraryView() {
  const load = useCallback(() => workspaceService.listLibrary(), []);
  const { state, reload } = useServiceData(load);
  const { openLibraryDocument } = useAppActions();
  const [field, setField] = useState<LibraryFilterField>(DEFAULT_LIBRARY_FIELD);
  const [filter, setFilter] = useState<LibraryFilter>(EMPTY_LIBRARY_FILTER);

  const documents = useMemo(() => (state.status === "success" ? state.data : []), [state]);
  const kindCounts = useMemo(() => countByKind(documents), [documents]);
  const visible = useMemo(() => filterLibrary(documents, filter), [documents, filter]);
  const groups = useMemo(() => groupByMonth(visible), [visible]);
  const filtered = visible.length !== documents.length;

  return (
    <ViewContainer>
      <ViewHeader
        title="문서 라이브러리"
        description="최종본까지 끝난 문서를 찾아 엽니다."
        action={
          state.status === "success" &&
          documents.length > 0 && (
            <p className="text-sm text-gray-500">
              {filtered && <span className="font-semibold text-blue-700">{visible.length}건 / </span>}
              전체 {documents.length}건
            </p>
          )
        }
      />

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} onRetry={reload} />}

      {state.status === "success" && documents.length === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white">
          <EmptyState
            icon={Library}
            title="아직 완성된 문서가 없습니다"
            description="작업이 최종본까지 끝나면 여기에 날짜·유형별로 모입니다."
          />
        </div>
      )}

      {state.status === "success" && documents.length > 0 && (
        <div className="flex flex-col gap-6">
          <LibraryFilterBar
            field={field}
            onFieldChange={setField}
            filter={filter}
            onFilterChange={setFilter}
            kindCounts={kindCounts}
          />

          {visible.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white">
              <EmptyState
                icon={SearchX}
                title="조건에 맞는 문서가 없습니다"
                description="검색어를 줄이거나 날짜 범위를 넓혀 보세요."
                action={
                  <Button size="sm" onClick={() => setFilter(EMPTY_LIBRARY_FILTER)}>
                    조건 지우기
                  </Button>
                }
              />
            </div>
          ) : (
            groups.map((group) => (
              <section key={group.key} aria-label={group.label}>
                <h2 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-gray-700">
                  {group.label}
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-gray-400 ring-1 ring-line">
                    {group.items.length}
                  </span>
                </h2>
                <ul className="grid gap-3 @2xl:grid-cols-2">
                  {group.items.map((doc) => (
                    <li key={`${doc.projectId}:${doc.kind}`}>
                      <LibraryDocumentCard doc={doc} onOpen={() => openLibraryDocument(doc.projectId, doc.artifactId)} />
                    </li>
                  ))}
                </ul>
              </section>
            ))
          )}
        </div>
      )}
    </ViewContainer>
  );
}
