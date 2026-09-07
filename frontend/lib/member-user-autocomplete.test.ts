import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import type { User } from "./api.ts";
import {
  memberUserSelectionAfterInput,
  nextMemberUserOptionIndex,
} from "./member-user-autocomplete-state.ts";

const component = readFileSync(
  new URL("../components/companies/member-user-autocomplete.tsx", import.meta.url),
  "utf8",
);
const companyPage = readFileSync(
  new URL("../app/empresas/[id]/page.tsx", import.meta.url),
  "utf8",
);
const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const avatar = readFileSync(
  new URL("../components/common/avatar.tsx", import.meta.url),
  "utf8",
);

const selected: User = {
  id: 18,
  nombre: "Juan Cruz Maletti",
  headline: "Técnico electrónico",
  ciudad: "Argentina, Buenos Aires",
  foto_perfil_url: null,
  experiencias: [],
};

test("editing the visible name invalidates the selected user id", () => {
  assert.equal(memberUserSelectionAfterInput(selected, selected.nombre)?.id, 18);
  assert.equal(memberUserSelectionAfterInput(selected, "Juan Cruz Moyano"), null);
});

test("keyboard navigation remains deterministic", () => {
  assert.equal(nextMemberUserOptionIndex(-1, "next", 2), 0);
  assert.equal(nextMemberUserOptionIndex(0, "next", 2), 1);
  assert.equal(nextMemberUserOptionIndex(1, "next", 2), 1);
  assert.equal(nextMemberUserOptionIndex(0, "previous", 2), 1);
});

test("autocomplete debounces, limits and cancels obsolete searches", () => {
  assert.match(component, /MIN_QUERY_LENGTH = 2/);
  assert.match(component, /DEBOUNCE_MS = 300/);
  assert.match(component, /RESULT_LIMIT = 10/);
  assert.match(component, /new AbortController\(\)/);
  assert.match(component, /requestSequence/);
  assert.match(component, /controller\.abort\(\)/);
});

test("results include avatar, name, headline and city with accessible controls", () => {
  assert.match(component, /<Avatar name=\{user\.nombre\} src=\{user\.foto_perfil_url\}/);
  assert.match(component, /\{user\.nombre\}/);
  assert.match(component, /user\.headline/);
  assert.match(component, /user\.ciudad/);
  assert.match(component, /role="combobox"/);
  assert.match(component, /role="listbox"/);
  assert.match(component, /role="option"/);
  assert.match(component, /ArrowDown/);
  assert.match(component, /ArrowUp/);
  assert.match(component, /event\.key === "Enter"/);
  assert.match(component, /event\.key === "Escape"/);
  assert.match(component, /document\.addEventListener\("pointerdown"/);
});

test("empty, loading and API error states stay inside the dropdown", () => {
  assert.match(component, /Buscando usuarios\.\.\./);
  assert.match(component, /No se encontraron usuarios\./);
  assert.match(component, /No se pudieron buscar usuarios\./);
  assert.match(component, /role="alert"/);
});

test("company form only submits the internally selected id", () => {
  assert.match(companyPage, /<MemberUserAutocomplete/);
  assert.match(companyPage, /selectedMemberUser\.id/);
  assert.match(companyPage, /if \(!selectedMemberUser\)/);
  assert.match(companyPage, /Seleccioná una persona de la lista\./);
  assert.match(companyPage, /disabled=\{busy \|\| !selectedMemberUser\}/);
  assert.doesNotMatch(companyPage, /ID de usuario|type="number"[^>]*usuario/);
});

test("requests are centralized and native dialogs are never used", () => {
  assert.match(api, /searchMemberCandidates/);
  assert.match(api, /\/api\/empresas\/\$\{id\}\/usuarios\/candidatos/);
  assert.match(api, /credentials: "include"/);
  assert.doesNotMatch(component, /\bfetch\s*\(/);
  assert.doesNotMatch(component + companyPage, /(?:window\.)?(?:alert|confirm|prompt)\s*\(/);
});

test("the shared Avatar component provides the existing no-photo fallback", () => {
  assert.match(avatar, /avatar-fallback/);
  assert.match(avatar, /Sin foto:/);
});
