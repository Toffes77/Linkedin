import type { User } from "@/lib/api";

export function nextMemberUserOptionIndex(
  current: number,
  direction: "next" | "previous",
  resultCount: number,
) {
  if (resultCount <= 0) return -1;
  if (direction === "next") return Math.min(current + 1, resultCount - 1);
  return current <= 0 ? resultCount - 1 : current - 1;
}

export function memberUserSelectionAfterInput(
  selectedUser: User | null,
  inputValue: string,
) {
  return selectedUser?.nombre === inputValue ? selectedUser : null;
}
