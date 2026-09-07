import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  citySelectionAfterInput,
  nextCityOptionIndex,
} from "./city-autocomplete-state.ts";

const component = readFileSync(
  new URL("../components/profile/city-autocomplete.tsx", import.meta.url),
  "utf8",
);
const registerPage = readFileSync(
  new URL("../app/registro/page.tsx", import.meta.url),
  "utf8",
);
const editPage = readFileSync(
  new URL("../app/perfil/editar/page.tsx", import.meta.url),
  "utf8",
);
const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");

test("editing selected text invalidates the city until it is selected again", () => {
  assert.equal(
    citySelectionAfterInput("Argentina, Buenos Aires", "Argentina, Buenos Aires"),
    "Argentina, Buenos Aires",
  );
  assert.equal(
    citySelectionAfterInput("Argentina, Buenos Aires", "Argentina, Buenos AiresXXX"),
    null,
  );
});

test("keyboard navigation has stable ArrowDown and ArrowUp behavior", () => {
  assert.equal(nextCityOptionIndex(-1, "next", 3), 0);
  assert.equal(nextCityOptionIndex(0, "next", 3), 1);
  assert.equal(nextCityOptionIndex(2, "next", 3), 2);
  assert.equal(nextCityOptionIndex(-1, "previous", 3), 2);
  assert.equal(nextCityOptionIndex(0, "previous", 3), 2);
});

test("autocomplete debounces, aborts obsolete requests and waits for two characters", () => {
  assert.match(component, /MIN_QUERY_LENGTH = 2/);
  assert.match(component, /DEBOUNCE_MS = 300/);
  assert.match(component, /new AbortController\(\)/);
  assert.match(component, /requestSequence/);
  assert.match(component, /window\.clearTimeout\(timeout\)/);
  assert.match(component, /controller\.abort\(\)/);
});

test("city options are accessible by keyboard, close on Escape and outside clicks", () => {
  assert.match(component, /role="combobox"/);
  assert.match(component, /role="listbox"/);
  assert.match(component, /role="option"/);
  assert.match(component, /ArrowDown/);
  assert.match(component, /ArrowUp/);
  assert.match(component, /event\.key === "Enter"/);
  assert.match(component, /event\.key === "Escape"/);
  assert.match(component, /document\.addEventListener\("pointerdown"/);
});

test("loading, empty and API failures remain inside the autocomplete", () => {
  assert.match(component, />Buscando\.\.\.<\/span>/);
  assert.match(component, /No se encontraron ciudades\./);
  assert.match(component, /No se pudieron cargar las ciudades\./);
  assert.match(component, /role="alert"/);
});

test("registration requires a selected city and sends only that canonical value", () => {
  assert.match(registerPage, /<CityAutocomplete/);
  assert.match(registerPage, /if \(!selectedCity\)/);
  assert.match(registerPage, /Seleccioná una ciudad de la lista\./);
  assert.match(registerPage, /usersApi\.create\(\{ \.\.\.data, ciudad: selectedCity \}\)/);
});

test("profile editing starts from the existing city and invalid selection blocks saving", () => {
  assert.match(editPage, /selectedCity === undefined \? user\.ciudad : selectedCity/);
  assert.match(editPage, /if \(!city\)/);
  assert.match(editPage, /<CityAutocomplete selectedCity=\{profileCity\}/);
});

test("all city requests use the centralized API and no native alert", () => {
  assert.match(api, /locationsApi/);
  assert.match(api, /\/api\/ubicaciones\/ciudades/);
  assert.match(api, /credentials: "include"/);
  assert.doesNotMatch(component, /\bfetch\s*\(/);
  assert.doesNotMatch(component + registerPage + editPage, /(?:window\.)?(?:alert|confirm)\s*\(/);
});
