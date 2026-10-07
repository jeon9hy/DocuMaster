import { File, FileImage, FileText, Presentation, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ArtifactFileType } from "@/types";

const ICONS: Record<ArtifactFileType, { icon: LucideIcon; className: string }> = {
  markdown: { icon: FileText, className: "bg-primary/8 text-primary" },
  pdf: { icon: FileText, className: "bg-negative/8 text-negative-fg" },
  image: { icon: FileImage, className: "bg-positive/8 text-positive-fg" },
  pptx: { icon: Presentation, className: "bg-accent-orange/8 text-accent-orange" },
  file: { icon: File, className: "bg-fill text-label-alternative" },
};

export function ArtifactIcon({ fileType, className }: { fileType: ArtifactFileType; className?: string }) {
  const { icon: Icon, className: tone } = ICONS[fileType];
  return (
    <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg", tone, className)}>
      <Icon className="size-4" aria-hidden />
    </span>
  );
}
