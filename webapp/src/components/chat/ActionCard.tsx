"use client";

import { useState, type FormEvent } from "react";
import { CheckCircle2, CircleAlert, Lock } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { UserInputRequest } from "@/types";
import { MarkdownLite } from "../artifact/MarkdownLite";
import { Button } from "../ui/Button";

interface ActionCardProps {
  request: UserInputRequest;
  /** 아직 응답을 기다리는 중인지. 응답이 끝나면 접힌 기록으로 남는다. */
  pending: boolean;
  /** Guest(읽기 전용)면 선택지 대신 로그인 안내만 보여 준다 */
  canRespond: boolean;
  createdAt: string;
  onRespond: (promptId: string, answer: string) => Promise<void>;
}

/**
 * 사용자 판단이 필요할 때(모드 애매·범위 충돌·검증 blocked 등) 피드에 뜨는 카드.
 * 일반 대화와 구분되도록 테두리·색을 달리한다. 선택지 버튼 또는 자유 입력으로 답한다.
 */
export function ActionCard({ request, pending, canRespond, createdAt, onRespond }: ActionCardProps) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const respond = async (answer: string) => {
    if (!answer.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      await onRespond(request.promptId, answer.trim());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "응답을 보내지 못했습니다.");
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void respond(text);
  };

  return (
    <section
      aria-label={`사용자 확인 필요: ${request.title}`}
      className={cn(
        "ml-[52px] rounded-xl border px-4 py-3",
        pending ? "border-amber-300 bg-amber-50/70 shadow-sm" : "border-line bg-white opacity-80",
      )}
    >
      <header className="flex items-center gap-2">
        {pending ? (
          <CircleAlert className="size-4 shrink-0 text-amber-600" aria-hidden />
        ) : (
          <CheckCircle2 className="size-4 shrink-0 text-emerald-500" aria-hidden />
        )}
        <h3 className="min-w-0 flex-1 text-sm font-semibold text-gray-900">
          {pending ? "사용자 확인 필요" : "응답 완료"} · {request.title}
        </h3>
        <span className="shrink-0 text-[11px] text-gray-400">{formatTime(createdAt)}</span>
      </header>

      {pending && (
        <div className="mt-2 space-y-3">
          <div className="max-h-80 overflow-y-auto text-sm text-gray-700">
            <MarkdownLite text={request.message} />
          </div>
          {!canRespond && (
            <p className="flex items-center gap-1.5 text-xs text-gray-500">
              <Lock className="size-3.5 shrink-0" aria-hidden />
              로그인하면 여기서 답할 수 있습니다.
            </p>
          )}
          {canRespond && request.choices.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {request.choices.map((choice) => (
                <Button key={choice} size="sm" disabled={sending} onClick={() => respond(choice)}>
                  {choice}
                </Button>
              ))}
            </div>
          )}
          {canRespond && request.allowFreeText && (
            <form onSubmit={handleSubmit} className="flex items-end gap-2">
              <textarea
                rows={1}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="직접 답하기…"
                aria-label="직접 답하기"
                className="field-sizing-content max-h-32 min-h-8 flex-1 resize-none rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
              <Button size="sm" variant="primary" type="submit" disabled={!text.trim() || sending}>
                답변 보내기
              </Button>
            </form>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
      )}
    </section>
  );
}
