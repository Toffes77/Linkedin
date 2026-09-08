import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  getProfileCompletionCardState,
  getProfileCompletion,
  markProfileCompletionActionStarted,
  markProfileCompletionShown,
  profileCompletionPendingKey,
  profileCompletionSeenKey,
  shouldShowProfileCompleted,
} from "./profile-completion.ts";

type StoredValues = Map<string, string>;

function storage(values: StoredValues = new Map()) {
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

const profile = (id: number, overrides: Partial<{ nombre: string; headline: string; ciudad: string; foto_perfil_url: string | null }> = {}) => ({
  id,
  nombre: "Ana",
  headline: "Diseñadora",
  ciudad: "Buenos Aires",
  foto_perfil_url: null,
  ...overrides,
});

test("calcula 0/2, 1/2 y 2/2 desde los datos reales del usuario", () => {
  assert.equal(getProfileCompletion(profile(1, { nombre: "", headline: "", ciudad: "" })).completed, 0);
  assert.equal(getProfileCompletion(profile(1)).completed, 1);
  assert.equal(getProfileCompletion(profile(1, { foto_perfil_url: "/foto.png" })).completed, 2);
});

test("la tarjeta pendiente solo ofrece agregar foto de perfil", () => {
  const component = readFileSync(new URL("../components/feed/profile-completion-card.tsx", import.meta.url), "utf8");
  assert.match(component, />Agregar foto de perfil<\/strong>/);
  assert.match(component, /href="\/perfil\/editar\?tab=photo"/);
  assert.doesNotMatch(component, /Agregar experiencia/);
});

test("un usuario que ya tenía foto no recibe la tarjeta ni la confirmación", () => {
  const values = new Map<string, string>();
  const user = profile(1, { foto_perfil_url: "/foto.png" });
  assert.equal(shouldShowProfileCompleted(user, storage(values)), false);
  assert.equal(getProfileCompletionCardState(user, storage(values)), "hidden");
});

test("al volver después de subir la foto desde la tarjeta muestra una sola confirmación", () => {
  const values = new Map<string, string>();
  const localStorage = storage(values);
  const user = profile(1, { foto_perfil_url: "/foto.png" });

  markProfileCompletionActionStarted(user.id, localStorage);
  assert.equal(shouldShowProfileCompleted(user, localStorage), true);
  assert.equal(getProfileCompletionCardState(user, localStorage), "completed");
  markProfileCompletionShown(user.id, localStorage);
  assert.equal(shouldShowProfileCompleted(user, localStorage), false);
  assert.equal(getProfileCompletionCardState(user, localStorage), "hidden");
  assert.equal(values.get(profileCompletionSeenKey(user.id)), "true");
  assert.equal(values.has(profileCompletionPendingKey(user.id)), false);
});

test("la confirmación persistida se aísla por usuario", () => {
  const values = new Map<string, string>();
  const localStorage = storage(values);
  markProfileCompletionActionStarted(2, localStorage);

  assert.equal(shouldShowProfileCompleted(profile(1, { foto_perfil_url: "/foto.png" }), localStorage), false);
  assert.equal(shouldShowProfileCompleted(profile(2, { foto_perfil_url: "/foto.png" }), localStorage), true);
});

test("Premium ya no se renderiza dentro del lateral del feed", () => {
  const profileCard = readFileSync(new URL("../components/feed/profile-card.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(profileCard, /premium-card|Premium/);
});
