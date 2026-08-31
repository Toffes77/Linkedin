import type { ReactionCounts, ReactionType } from "@/lib/api";

export function countsAfterReaction(
  counts: ReactionCounts | null,
  current: ReactionType | null,
  next: ReactionType,
): ReactionCounts | null {
  if (!counts) return counts;
  const updated = { ...counts };
  if (current && current !== next) {
    updated[current] = Math.max(0, updated[current] - 1);
  }
  if (current !== next) updated[next] += 1;
  return updated;
}

export function countsAfterRemoval(
  counts: ReactionCounts | null,
  current: ReactionType,
): ReactionCounts | null {
  if (!counts) return counts;
  return { ...counts, [current]: Math.max(0, counts[current] - 1) };
}
