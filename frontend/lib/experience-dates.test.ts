import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { getLocalDateForInput, validateExperienceDates } from "./experience-dates.ts";

const profilePage = readFileSync(
  new URL("../app/perfil/editar/page.tsx", import.meta.url),
  "utf8",
);
const dateHelpers = readFileSync(new URL("./experience-dates.ts", import.meta.url), "utf8");

test("experience date helper formats the local calendar date without UTC conversion", () => {
  assert.equal(getLocalDateForInput(new Date(2026, 8, 8, 0, 30)), "2026-09-08");
  assert.doesNotMatch(dateHelpers, /toISOString/);
});

test("experience date validation accepts valid civil dates and rejects invalid combinations", () => {
  const today = "2026-09-08";
  assert.equal(validateExperienceDates({ desde: "2025-03-10", hasta: "2026-09-08" }, today), null);
  assert.equal(validateExperienceDates({ desde: today, hasta: "" }, today), null);
  assert.equal(validateExperienceDates({ desde: "2025-01-01", hasta: "" }, today), null);
  assert.equal(validateExperienceDates({ desde: "2026-09-09", hasta: "" }, today), "La fecha de inicio no puede ser posterior a hoy.");
  assert.equal(validateExperienceDates({ desde: "2025-01-01", hasta: "2026-09-09" }, today), "La fecha de finalización no puede ser posterior a hoy.");
  assert.equal(validateExperienceDates({ desde: "2026-05-01", hasta: "2026-04-01" }, today), "La fecha de finalización no puede ser anterior a la fecha de inicio.");
});

test("experience form preserves edit values and blocks manipulated future dates before requests", () => {
  assert.equal((profilePage.match(/max=\{maxExperienceDate\}/g) ?? []).length, 2);
  assert.match(profilePage, /desde: item\.desde,[\s\S]*hasta: item\.hasta \?\? "",/);
  assert.match(profilePage, /desde: experience\.desde,[\s\S]*hasta: experience\.hasta \|\| null,/);
  assert.match(profilePage, /const dateError = validateExperienceDates\(experience, getLocalDateForInput\(\)\);[\s\S]*if \(dateError\) \{[\s\S]*return;/);
  assert.equal((profilePage.match(/validity\.rangeOverflow/g) ?? []).length, 2);
  assert.match(profilePage, /await refreshUser\(\);[\s\S]*resetExperienceForm\(\);/);
  assert.doesNotMatch(profilePage, /toISOString/);
});
