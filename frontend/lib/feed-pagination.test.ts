import assert from "node:assert/strict";
import test from "node:test";

import {
  appendUniqueById,
  canRequestFeedPage,
  excludeItemById,
  feedHasMore,
  uniqueById,
} from "./feed-pagination.ts";

const firstPage = [{ id: 1 }, { id: 2 }, { id: 3 }];

test("new pages append below existing posts without replacing them", () => {
  assert.deepEqual(
    appendUniqueById(firstPage, [{ id: 4 }, { id: 5 }]).map((item) => item.id),
    [1, 2, 3, 4, 5],
  );
});

test("duplicates inside and across pages are removed while order stays stable", () => {
  assert.deepEqual(
    appendUniqueById(firstPage, [{ id: 3 }, { id: 4 }, { id: 4 }]).map(
      (item) => item.id,
    ),
    [1, 2, 3, 4],
  );
  assert.deepEqual(uniqueById([{ id: 8 }, { id: 8 }, { id: 9 }]), [
    { id: 8 },
    { id: 9 },
  ]);
});

test("a temporarily pinned shared post is excluded from normal feed pages", () => {
  assert.deepEqual(
    excludeItemById([{ id: 32 }, { id: 90 }, { id: 89 }], 32),
    [{ id: 90 }, { id: 89 }],
  );
  assert.deepEqual(excludeItemById([{ id: 90 }], null), [{ id: 90 }]);
});

test("a short or empty page marks the end of the feed", () => {
  assert.equal(feedHasMore(10, 10), true);
  assert.equal(feedHasMore(9, 10), false);
  assert.equal(feedHasMore(0, 10), false);
});

test("loading, exhausted and already loaded pages cannot be requested again", () => {
  const loadedPages = new Set([1, 2]);
  assert.equal(canRequestFeedPage(3, false, true, loadedPages), true);
  assert.equal(canRequestFeedPage(2, false, true, loadedPages), false);
  assert.equal(canRequestFeedPage(3, true, true, loadedPages), false);
  assert.equal(canRequestFeedPage(3, false, false, loadedPages), false);
});
