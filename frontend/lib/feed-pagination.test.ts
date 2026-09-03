import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  appendUniqueById,
  canRequestFeedCursor,
  excludeItemById,
  failedFeedContinuation,
  feedQueryParams,
  releaseFailedFeedCursor,
  successfulFeedContinuation,
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

test("a transient error preserves the pending cursor and allows manual retry", () => {
  const requestedCursors = new Set(["cursor-page-2"]);
  const failed = failedFeedContinuation(
    "cursor-page-2",
    true,
    "No se pudo cargar más contenido",
  );

  releaseFailedFeedCursor(requestedCursors, "cursor-page-2");

  assert.deepEqual(failed, {
    cursor: "cursor-page-2",
    hasMore: true,
    loadError: "No se pudo cargar más contenido",
  });
  assert.equal(
    canRequestFeedCursor(failed.cursor, false, failed.hasMore, requestedCursors),
    true,
  );
});

test("repeated errors never become end-of-feed and keep existing items", () => {
  const existing = [{ id: 1 }, { id: 2 }];
  const firstFailure = failedFeedContinuation("cursor-page-2", true, "fallo 1");
  const secondFailure = failedFeedContinuation(
    firstFailure.cursor!,
    firstFailure.hasMore,
    "fallo 2",
  );

  assert.deepEqual(existing.map((item) => item.id), [1, 2]);
  assert.equal(secondFailure.cursor, "cursor-page-2");
  assert.equal(secondFailure.hasMore, true);
  assert.equal(secondFailure.loadError, "fallo 2");
});

test("successful retry advances once without duplicates and real end clears hasMore", () => {
  const afterRetry = appendUniqueById(firstPage, [{ id: 3 }, { id: 4 }]);
  const next = successfulFeedContinuation("cursor-page-3", true);
  const end = successfulFeedContinuation(null, false);

  assert.deepEqual(afterRetry.map((item) => item.id), [1, 2, 3, 4]);
  assert.deepEqual(next, {
    cursor: "cursor-page-3",
    hasMore: true,
    loadError: "",
  });
  assert.deepEqual(end, { cursor: null, hasMore: false, loadError: "" });
});

test("feed cards and related pages do not mount per-item metadata requests", () => {
  const feedPage = readFileSync(
    new URL("../app/feed/page.tsx", import.meta.url),
    "utf8",
  );
  const postCard = readFileSync(
    new URL("../components/feed/post-card.tsx", import.meta.url),
    "utf8",
  );
  const profilePage = readFileSync(
    new URL("../app/perfil/[id]/page.tsx", import.meta.url),
    "utf8",
  );
  const jobsPage = readFileSync(
    new URL("../app/empleos/page.tsx", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(feedPage, /usersApi\.get/);
  assert.doesNotMatch(postCard, /reactionCounts|myReaction|commentsApi\.count/);
  assert.match(profilePage, /companiesApi\.getBatch/);
  assert.doesNotMatch(profilePage, /ids\.map\([^)]*companiesApi\.get/);
  assert.match(jobsPage, /companiesApi\.getBatch/);
  assert.doesNotMatch(jobsPage, /companyIds\.map\([^)]*companiesApi\.get/);
});
