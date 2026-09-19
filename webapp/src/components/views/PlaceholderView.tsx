import { Construction } from "lucide-react";
import { EmptyState } from "../ui/States";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 1차 프로토타입에서 자리만 잡아 둔 화면 */
export function PlaceholderView({ title, description }: { title: string; description: string }) {
  return (
    <ViewContainer>
      <ViewHeader title={title} />
      <div className="rounded-xl border border-dashed border-gray-300 bg-white">
        <EmptyState icon={Construction} title="준비 중인 화면입니다" description={description} />
      </div>
    </ViewContainer>
  );
}
