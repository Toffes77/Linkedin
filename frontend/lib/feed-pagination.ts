type Identifiable = { id: number };

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

export function feedHasMore(receivedCount: number, pageSize: number) {
  return receivedCount === pageSize;
}

export function canRequestFeedPage(
  page: number,
  loading: boolean,
  hasMore: boolean,
  loadedPages: ReadonlySet<number>,
) {
  return !loading && hasMore && !loadedPages.has(page);
}
