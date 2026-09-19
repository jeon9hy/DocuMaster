"use client";

import { useCallback, useState, type ReactNode } from "react";
import { AddReferenceModal } from "./AddReferenceModal";

/**
 * 레퍼런스 추가 모달을 여는 버튼. 버튼 모양은 쓰는 곳마다 달라서 render prop으로 받는다.
 * 예: <AddReferenceButton>{(open) => <Button onClick={open}>추가</Button>}</AddReferenceButton>
 */
export function AddReferenceButton({ children }: { children: (open: () => void) => ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  return (
    <>
      {children(open)}
      <AddReferenceModal open={isOpen} onClose={close} />
    </>
  );
}
