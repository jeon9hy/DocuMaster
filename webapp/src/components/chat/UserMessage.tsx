import { formatTime } from "@/lib/format";
import { splitMentions } from "@/lib/mentions";

export function UserMessage({ text, createdAt }: { text: string; createdAt: string }) {
  return (
    <article className="flex flex-col items-end">
      <p className="max-w-[560px] rounded-xl rounded-tr-sm bg-blue-600 px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line text-white">
        {splitMentions(text).map((segment, index) =>
          segment.mention ? (
            <strong key={index} className="font-semibold text-blue-100">
              {segment.text}
            </strong>
          ) : (
            segment.text
          ),
        )}
      </p>
      <time className="mt-1 text-xs text-gray-400" dateTime={createdAt}>
        나 · {formatTime(createdAt)}
      </time>
    </article>
  );
}
