import assert from "node:assert/strict";
import test from "node:test";

import {
  appendUniqueById,
  canRequestFeedCursor,
  excludeItemById,
  feedQueryParams,
  uniqueById,
} from "./feed-pagination.ts";

const firstPage = [{ id: 1 }, { id: 2 }, { id: 3 }];

test("the first request has no cursor and continuation sends the backend cursor", () => {
  assert.equal(feedQueryParams({ pageSize: 10 }).toString(), "page_size=10");
  assert.equal(
    feedQueryParams({
      cursor: "signed.cursor",
      pageSize: 10,
      excludePostId: 32,
    }).toString(),
    "page_size=10&cursor=signed.cursor&exclude_publicacion_id=32",
  );
});

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

test("loading, exhausted and already requested cursors cannot be requested again", () => {
  const requestedCursors = new Set(["cursor-1"]);
  assert.equal(canRequestFeedCursor("cursor-2", false, true, requestedCursors), true);
  assert.equal(canRequestFeedCursor("cursor-1", false, true, requestedCursors), false);
  assert.equal(canRequestFeedCursor("cursor-2", true, true, requestedCursors), false);
  assert.equal(canRequestFeedCursor("cursor-2", false, false, requestedCursors), false);
  assert.equal(canRequestFeedCursor(null, false, true, requestedCursors), false);
});
