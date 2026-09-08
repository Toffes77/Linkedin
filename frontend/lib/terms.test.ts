import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const terms = readFileSync(new URL("../content/terminos.md", import.meta.url), "utf8");
const termsPage = readFileSync(new URL("../app/terminos/page.tsx", import.meta.url), "utf8");
const registerPage = readFileSync(new URL("../app/registro/page.tsx", import.meta.url), "utf8");
const loginPage = readFileSync(new URL("../app/login/page.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

test("la página pública de términos lee el documento completo sin protección de sesión", () => {
  assert.match(termsPage, /readFileSync/);
  assert.match(termsPage, /content["']?,\s*["']terminos\.md/);
  assert.match(termsPage, /renderMarkdown\(markdown\)/);
  assert.match(termsPage, /Volver a iniciar sesión/);
  assert.doesNotMatch(termsPage, /ProtectedPage|AppShell/);
  assert.match(terms, /# Términos y Condiciones de Atanes/);
  assert.match(terms, /## 13\. Datos, cookies y almacenamiento técnico/);
  assert.match(terms, /HttpOnly/);
  assert.match(terms, /SameSite=Lax/);
  assert.match(terms, /PostgreSQL/);
  assert.match(styles, /\.legal-document \{ width:min\(820px/);
  assert.match(styles, /@media \(max-width:520px\)/);
  assert.match(styles, /\.legal-document \{ width:100%;/);
});

test("el registro exige la casilla y envía acepta_terminos", () => {
  assert.match(registerPage, /useState\(false\)/);
  assert.match(registerPage, /type="checkbox"/);
  assert.match(registerPage, /checked=\{acceptsTerms\}/);
  assert.match(registerPage, /Acepto los <Link href="\/terminos">Términos y Condiciones/);
  assert.match(registerPage, /disabled=\{busy \|\| !acceptsTerms\}/);
  assert.match(registerPage, /acepta_terminos: acceptsTerms/);
  assert.doesNotMatch(registerPage, /Política de Privacidad|política de privacidad/);
});

test("las pantallas de autenticación enlazan la única página de términos", () => {
  assert.match(loginPage, /href="\/terminos"/);
  assert.doesNotMatch(loginPage, /Política de privacidad/);
});
