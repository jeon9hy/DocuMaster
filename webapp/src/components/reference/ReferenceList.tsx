import { FileText, Image as ImageIcon, Link2, Paperclip, Type, type LucideIcon } from "lucide-react";
import { formatDay } from "@/lib/format";
import type { Reference, ReferenceKind } from "@/types";
import { EmptyState } from "../ui/States";

const KIND_ICON: Record<ReferenceKind, { icon: LucideIcon; className: string }> = {
  pdf: { icon: FileText, className: "bg-red-50 text-red-600" },
  image: { icon: ImageIcon, className: "bg-sky-50 text-sky-600" },
  url: { icon: Link2, className: "bg-blue-50 text-blue-600" },
  text: { icon: Type, className: "bg-gray-100 text-gray-600" },
  markdown: { icon: FileText, className: "bg-gray-100 text-gray-600" },
  file: { icon: Paperclip, className: "bg-gray-100 text-gray-600" },
};

function ReferenceItem({ reference }: { reference: Reference }) {
  const { icon: Icon, className } = KIND_ICON[reference.kind];
  return (
    <li className="flex items-center gap-2.5 rounded-lg px-2 py-1.5">
      <span className={`flex size-7 shrink-0 items-center justify-center rounded-md ${className}`}>
        <Icon className="size-3.5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-medium text-gray-800">{reference.name}</span>
        <span className="block truncate text-xs text-gray-500">
          {reference.detail} · {formatDay(reference.addedAt)}
        </span>
      </span>
    </li>
  );
}

export function ReferenceList({ references }: { references: Reference[] }) {
  if (references.length === 0) {
    return <EmptyState icon={Paperclip} title="레퍼런스가 없습니다" className="py-4" />;
  }
  return (
    <ul className="space-y-0.5">
      {references.map((reference) => (
        <ReferenceItem key={reference.id} reference={reference} />
      ))}
    </ul>
  );
}
