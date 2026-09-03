import type { Comment } from "./api";

export type CommentChildrenPage = {
  items: Comment[];
  nextCursor: string | null;
  hasMore: boolean;
  loading: boolean;
  error: string;
};

export type VisibleCommentRow =
  | { kind: "comment"; comment: Comment; depth: number }
  | { kind: "control"; parentId: number; depth: number };

export function mergeCommentPage(items: Comment[], additions: Comment[]): Comment[] {
  const byId = new Map(items.map((item) => [item.id, item]));
  additions.forEach((item) => byId.set(item.id, item));
  return [...byId.values()].sort((left, right) => new Date(left.fecha).getTime() - new Date(right.fecha).getTime() || left.id - right.id);
}

export function buildVisibleCommentRows(
  roots: Comment[],
  openIds: Set<number>,
  children: Record<number, CommentChildrenPage>,
): VisibleCommentRow[] {
  const rows: VisibleCommentRow[] = [];
  const stack: VisibleCommentRow[] = roots.slice().reverse().map((comment) => ({ kind: "comment", comment, depth: 0 }));
  while (stack.length) {
    const row = stack.pop()!;
    rows.push(row);
    if (row.kind !== "comment" || !openIds.has(row.comment.id)) continue;
    const page = children[row.comment.id];
    stack.push({ kind: "control", parentId: row.comment.id, depth: row.depth + 1 });
    if (page) for (let index = page.items.length - 1; index >= 0; index -= 1) stack.push({ kind: "comment", comment: page.items[index], depth: row.depth + 1 });
  }
  return rows;
}
