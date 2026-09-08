import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { getMostRecentExperience } from "./experience-recency.ts";
import { formatDateArgentina } from "./format.ts";

type FixtureExperience = {
  id: number;
  empresa_id: number;
  puesto: string;
  desde: string;
  hasta: string | null;
};

const profileCard = readFileSync(
  new URL("../components/feed/profile-card.tsx", import.meta.url),
  "utf8",
);
const publicProfilePage = readFileSync(
  new URL("../app/perfil/[id]/page.tsx", import.meta.url),
  "utf8",
);
const editProfilePage = readFileSync(
  new URL("../app/perfil/editar/page.tsx", import.meta.url),
  "utf8",
);
const jobsPage = readFileSync(new URL("../app/empleos/page.tsx", import.meta.url), "utf8");
const jobDetailPage = readFileSync(new URL("../app/empleos/[id]/page.tsx", import.meta.url), "utf8");

function experience(overrides: Partial<FixtureExperience>): FixtureExperience {
  return {
    id: 1,
    empresa_id: 1,
    puesto: "Developer",
    desde: "2022-01-01",
    hasta: "2022-12-31",
    ...overrides,
  };
}

test("feed chooses the latest finished experience regardless of insertion order", () => {
  const earlier = experience({ id: 1, puesto: "Empresa A", desde: "2022-03-01", hasta: "2023-07-20" });
  const later = experience({ id: 2, puesto: "Empresa B", desde: "2024-02-10", hasta: "2025-08-15" });

  assert.equal(getMostRecentExperience([earlier, later])?.id, later.id);
  assert.equal(getMostRecentExperience([later, earlier])?.id, later.id);
});

test("a current experience has priority and ties are deterministic", () => {
  const current = experience({ id: 1, puesto: "Actual", desde: "2024-01-01", hasta: null });
  const newerFinished = experience({ id: 2, puesto: "Finalizada", desde: "2025-01-01", hasta: "2026-01-01" });
  assert.equal(getMostRecentExperience([newerFinished, current])?.id, current.id);

  const sameEndEarlierStart = experience({ id: 3, desde: "2024-01-01", hasta: "2025-08-15" });
  const sameEndLaterStart = experience({ id: 4, desde: "2024-02-01", hasta: "2025-08-15" });
  const exactTieHigherId = experience({ id: 5, desde: "2024-02-01", hasta: "2025-08-15" });
  assert.equal(getMostRecentExperience([sameEndEarlierStart, sameEndLaterStart])?.id, sameEndLaterStart.id);
  assert.equal(getMostRecentExperience([sameEndLaterStart, exactTieHigherId])?.id, exactTieHigherId.id);
});

test("experience and job publication dates use the Argentine display format only", () => {
  assert.equal(formatDateArgentina("2026-09-08"), "08/09/2026");
  assert.equal(formatDateArgentina(null), "Actualidad");
  assert.match(profileCard, /getMostRecentExperience\(user\.experiencias\)/);
  assert.doesNotMatch(profileCard, /experiencias\[0\]/);
  assert.match(publicProfilePage, /formatDateArgentina\(experience\.desde\)/);
  assert.match(publicProfilePage, /formatDateArgentina\(experience\.hasta\)/);
  assert.match(editProfilePage, /formatDateArgentina\(item\.desde\)/);
  assert.match(editProfilePage, /formatDateArgentina\(item\.hasta\)/);
  assert.match(jobsPage, /formatDateArgentina\(job\.fecha_publicacion\)/);
  assert.match(jobDetailPage, /formatDateArgentina\(job\.fecha_publicacion\)/);
  assert.match(editProfilePage, /<input type="date" required max=\{maxExperienceDate\} value=\{experience\.desde\}/);
  assert.match(editProfilePage, /<input type="date" max=\{maxExperienceDate\} value=\{experience\.hasta\}/);
});
