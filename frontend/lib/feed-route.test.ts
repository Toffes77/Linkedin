import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const feedLayout = readFileSync(new URL("../app/feed/layout.tsx", import.meta.url), "utf8");
const feedPage = readFileSync(new URL("../app/feed/page.tsx", import.meta.url), "utf8");
const homePage = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const loginPage = readFileSync(new URL("../app/login/page.tsx", import.meta.url), "utf8");

test("/feed has a suspense fallback when its client page unwraps searchParams", () => {
  assert.match(feedPage, /use\(searchParams\)/);
  assert.match(feedLayout, /<Suspense fallback=\{<SessionLoader \/>\}>/);
  assert.match(feedPage, /if \(!user\) return <AppShell>\{null\}<\/AppShell>;/);
});

test("/feed remains the canonical post-login route", () => {
  assert.match(homePage, /user \? "\/feed" : "\/login"/);
  assert.match(loginPage, /router\.replace\("\/feed"\)/);
});
