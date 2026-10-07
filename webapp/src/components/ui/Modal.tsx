"use client";

import type { ReactNode } from "react";
import { Modal as WdsModal, ModalContainer, ModalContent, ModalContentItem, ModalNavigation } from "@wanteddev/wds";
import { cn } from "@/lib/cn";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  footer?: ReactNode;
  size?: "md" | "lg";
  children: ReactNode;
}

/** Montage 팝업. 바깥 누르기·Esc·초점 가두기·스크롤 잠금은 Montage가 한다. lg는 넓은 미리보기용(768px). */
export function Modal({ open, title, onClose, footer, size = "md", children }: ModalProps) {
  return (
    <WdsModal open={open} onOpenChange={(next) => !next && onClose()}>
      <ModalContainer
        variant="popup"
        size={size === "md" ? "large" : "xlarge"}
        sticky
        aria-label={title}
        className={cn("max-h-[90vh]", size === "lg" && "w-3xl")}
      >
        <ModalNavigation>{title}</ModalNavigation>
        <ModalContent>
          {/* 좌우 여백은 Montage가 준다. 안쪽 세로 간격은 각 모달이 정하므로 flex를 끈다 */}
          <ModalContentItem className="block">{children}</ModalContentItem>
        </ModalContent>
        {footer && <footer className="flex justify-end gap-2 px-6 pb-6">{footer}</footer>}
      </ModalContainer>
    </WdsModal>
  );
}
