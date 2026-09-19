import { AGENT_IDS, AGENT_PROFILES } from "@/constants/agents";
import type { AgentId } from "@/types";

const MENTION_PATTERN = new RegExp(
  `@(${AGENT_IDS.map((id) => AGENT_PROFILES[id].name).join("|")})`,
  "g",
);

const AGENT_BY_NAME = new Map<string, AgentId>(
  AGENT_IDS.map((id) => [AGENT_PROFILES[id].name, id]),
);

/** 지시문에서 처음 @로 부른 에이전트 */
export function findMentionedAgent(text: string): AgentId | undefined {
  const match = text.match(new RegExp(MENTION_PATTERN.source));
  return match ? AGENT_BY_NAME.get(match[1]) : undefined;
}

export type TextSegment = { text: string; mention: boolean };

/** "@요르 확인해 줘" → [{@요르, mention}, { 확인해 줘}] — 화면에서 @이름만 강조하려고 쓴다 */
export function splitMentions(text: string): TextSegment[] {
  const segments: TextSegment[] = [];
  let last = 0;
  for (const match of text.matchAll(MENTION_PATTERN)) {
    const start = match.index ?? 0;
    if (start > last) segments.push({ text: text.slice(last, start), mention: false });
    segments.push({ text: match[0], mention: true });
    last = start + match[0].length;
  }
  if (last < text.length) segments.push({ text: text.slice(last), mention: false });
  return segments;
}
