import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { carouselIndex, postMediaGrid } from "./post-media.ts";

const composer = readFileSync(new URL("../components/feed/composer.tsx", import.meta.url), "utf8");
const grid = readFileSync(new URL("../components/feed/post-media-grid.tsx", import.meta.url), "utf8");
const viewer = readFileSync(new URL("../components/feed/media-viewer.tsx", import.meta.url), "utf8");
const card = readFileSync(new URL("../components/feed/post-card.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");

test("the feed exposes four tiles and the exact overflow count", () => {
  const items = ["image", "video", "image", "video", "image", "video", "image"];
  const result = postMediaGrid(items);

  assert.deepEqual(result.visible, items.slice(0, 4));
  assert.equal(result.hiddenCount, 3);
  assert.match(grid, /index === 3 && hiddenCount > 0/);
  assert.match(grid, /\+\{hiddenCount\}/);
});

test("the carousel traverses and wraps every mixed media position", () => {
  const types = ["IMAGEN", "VIDEO", "IMAGEN", "VIDEO"];
  let index = 0;
  index = carouselIndex(index, 1, types.length);
  assert.equal(types[index], "VIDEO");
  index = carouselIndex(index, 1, types.length);
  assert.equal(types[index], "IMAGEN");
  index = carouselIndex(0, -1, types.length);
  assert.equal(index, 3);
  assert.match(viewer, /current\.tipo === "IMAGEN"/);
  assert.match(viewer, /<video key=\{current\.id\} src=\{source\} controls/);
  assert.match(viewer, /\{index \+ 1\} \/ \{items\.length\}/);
  assert.match(viewer, /ArrowLeft/);
  assert.match(viewer, /ArrowRight/);
  assert.match(viewer, /Escape/);
});

test("photo and video actions open distinct multiple file selectors", () => {
  assert.match(composer, /type="file" accept="image\/jpeg,image\/png,image\/webp" multiple/);
  assert.match(composer, /type="file" accept="video\/mp4,video\/webm" multiple/);
  assert.match(composer, /onClick=\{\(\) => choose\("image"\)\}/);
  assert.match(composer, /onClick=\{\(\) => choose\("video"\)\}/);
  assert.match(composer, /Quitar archivo/);
  assert.match(composer, /postsApi\.create\(text\.trim\(\), selected\.map/);
});

test("write article opens the same normal composer", () => {
  assert.match(composer, /onClick=\{\(\) => setOpen\(true\)\}><Icon name="write"\/>Escribir artículo/);
  assert.doesNotMatch(composer, /articuloApi|\/articulos|window\.open/);
});

test("uploads stay centralized and use multipart without overriding its content type", () => {
  assert.match(api, /new FormData\(\)/);
  assert.match(api, /body\.append\("archivos", file\)/);
  assert.match(api, /\/api\/publicaciones\/multimedia/);
  assert.match(api, /\/api\/publicaciones\/\$\{id\}\/multimedia/);
  assert.doesNotMatch(composer, /\bfetch\s*\(/);
  assert.doesNotMatch(card, /\bfetch\s*\(/);
});

test("editing handles existing and new media and deletion uses inline confirmation", () => {
  assert.match(card, /keptIds/);
  assert.match(card, /editMedia/);
  assert.match(card, /Quitar multimedia/);
  assert.match(card, /post-delete-confirm/);
  assert.doesNotMatch(card, /\b(?:window\.)?(?:alert|confirm|prompt)\s*\(/);
  assert.doesNotMatch(composer, /\b(?:window\.)?(?:alert|confirm|prompt)\s*\(/);
});
