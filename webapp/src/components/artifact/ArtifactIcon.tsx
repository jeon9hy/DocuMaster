import { File, FileImage, FileText, Presentation, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ArtifactFileType } from "@/types";

const ICONS: Record<ArtifactFileType, { icon: LucideIcon; className: string }> = {
  markdown: { icon: FileText, className: "bg-blue-50 text-blue-600" },
  pdf: { icon: FileText, className: "bg-red-50 text-red-600" },
  image: { icon: FileImage, className: "bg-emerald-50 text-emerald-600" },
  pptx: { icon: Presentation, className: "bg-orange-50 text-orange-600" },
  file: { icon: File, className: "bg-gray-100 text-gray-600" },
};

export function ArtifactIcon({ fileType, className }: { fileType: ArtifactFileType; className?: string }) {
  const { icon: Icon, className: tone } = ICONS[fileType];
  return (
    <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg", tone, className)}>
      <Icon className="size-4" aria-hidden />
    </span>
  );
}
