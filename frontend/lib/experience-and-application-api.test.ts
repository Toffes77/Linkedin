import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const profilePage = readFileSync(
  new URL("../app/perfil/editar/page.tsx", import.meta.url),
  "utf8",
);
const jobPage = readFileSync(
  new URL("../app/empleos/[id]/page.tsx", import.meta.url),
  "utf8",
);

test("experience client exposes owner-scoped update and delete routes", () => {
  assert.match(api, /updateExperience: \(experienceId: number/);
  assert.match(api, /\/api\/experiencias\/\$\{experienceId\}/);
  assert.match(api, /deleteExperience: \(experienceId: number\)/);
  assert.match(profilePage, /usersApi\.updateExperience/);
  assert.match(profilePage, /usersApi\.deleteExperience/);
  assert.match(profilePage, /¿Eliminar esta experiencia\?/);
  assert.doesNotMatch(profilePage, /(?:window\.)?(?:alert|confirm|prompt)\s*\(/);
});

test("job applications send only the offer id", () => {
  assert.match(api, /apply: \(jobId: number\)/);
  assert.match(api, /json: \{ oferta_id: jobId \}/);
  assert.doesNotMatch(api.match(/apply:.*$/m)?.[0] ?? "", /usuario_id/);
  assert.match(jobPage, /jobsApi\.apply\(id\)/);
  assert.doesNotMatch(jobPage, /jobsApi\.apply\(id,\s*user\.id\)/);
});
