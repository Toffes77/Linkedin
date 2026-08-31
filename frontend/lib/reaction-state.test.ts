import assert from "node:assert/strict";
import test from "node:test";

import { countsAfterReaction, countsAfterRemoval } from "./reaction-state.ts";

const counts = {
  like: 2,
  celebrar: 1,
  apoyar: 0,
  interesante: 0,
};

test("adding a reaction increments its count", () => {
  assert.deepEqual(countsAfterReaction(counts, null, "apoyar"), {
    ...counts,
    apoyar: 1,
  });
});

test("changing a reaction moves one count without duplicating", () => {
  assert.deepEqual(countsAfterReaction(counts, "like", "interesante"), {
    like: 1,
    celebrar: 1,
    apoyar: 0,
    interesante: 1,
  });
});

test("removing a reaction decrements only the selected type", () => {
  assert.deepEqual(countsAfterRemoval(counts, "celebrar"), {
    ...counts,
    celebrar: 0,
  });
});

test("counts never become negative after a repeated UI update", () => {
  assert.equal(countsAfterRemoval(counts, "apoyar")?.apoyar, 0);
});
