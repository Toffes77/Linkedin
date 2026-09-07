import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import type { CompanyRole } from "./api.ts";
import { getJobApplicationActionState } from "./job-application-state.ts";

for (const role of ["OWNER", "RECRUITER", "COLLABORATOR"] satisfies CompanyRole[]) {
  test(`${role} sees company membership instead of an apply action`, () => {
    const state = getJobApplicationActionState({
      membershipCheck: "ready",
      role,
      applied: false,
      busy: false,
    });

    assert.equal(state.showButton, false);
    assert.equal(state.membershipMessage, "Formás parte de esta empresa");
  });
}

test("an external user can apply", () => {
  const state = getJobApplicationActionState({
    membershipCheck: "ready",
    role: undefined,
    applied: false,
    busy: false,
  });

  assert.equal(state.showButton, true);
  assert.equal(state.disabled, false);
  assert.equal(state.label, "Postularme");
});

test("loading, errors and an existing application never leave an active button", () => {
  for (const current of [
    { membershipCheck: "loading" as const, applied: false, busy: false },
    { membershipCheck: "error" as const, applied: false, busy: false },
    { membershipCheck: "ready" as const, applied: true, busy: false },
    { membershipCheck: "ready" as const, applied: false, busy: true },
  ]) {
    const state = getJobApplicationActionState({ ...current, role: undefined });
    assert.equal(state.disabled, true);
  }
});

test("the job page reuses one membership request and renders API errors inline", () => {
  const page = readFileSync(
    new URL("../app/empleos/[id]/page.tsx", import.meta.url),
    "utf8",
  );

  assert.equal(page.match(/companiesApi\.mine\(\)/g)?.length, 1);
  assert.match(page, /getJobApplicationActionState/);
  assert.match(page, /role="alert"/);
  assert.doesNotMatch(page, /(?:window\.)?alert\s*\(/);
  assert.doesNotMatch(page, /(?:window\.)?confirm\s*\(/);
});
