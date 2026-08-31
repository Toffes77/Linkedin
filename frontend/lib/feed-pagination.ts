type Identifiable = { id: number };

export function feedQueryParams({
  cursor,
  pageSize,
  excludePostId,
}: {
  cursor?: string | null;
  pageSize: number;
  excludePostId?: number | null;
}) {
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (cursor) params.set("cursor", cursor);
  if (excludePostId) {
    params.set("exclude_publicacion_id", String(excludePostId));
  }
  return params;
}

export function uniqueById<Item extends Identifiable>(items: Item[]) {
  const seen = new Set<number>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

export function appendUniqueById<Item extends Identifiable>(
  current: Item[],
  incoming: Item[],
) {
  const existingIds = new Set(current.map((item) => item.id));
  return [
    ...current,
    ...uniqueById(incoming).filter((item) => !existingIds.has(item.id)),
  ];
}

export function excludeItemById<Item extends Identifiable>(
  items: Item[],
  excludedId: number | null | undefined,
) {
  return excludedId == null
    ? items
    : items.filter((item) => item.id !== excludedId);
}

export function canRequestFeedCursor(
  cursor: string | null,
  loading: boolean,
  hasMore: boolean,
  requestedCursors: ReadonlySet<string>,
) {
  return cursor !== null && !loading && hasMore && !requestedCursors.has(cursor);
}
