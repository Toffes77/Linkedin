import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const boardPage = readFileSync(new URL("../components/board/board-page.tsx", import.meta.url), "utf8");
const form = readFileSync(new URL("../components/board/promotion-form.tsx", import.meta.url), "utf8");
const hiringModal = readFileSync(new URL("../components/board/hiring-modal.tsx", import.meta.url), "utf8");
const card = readFileSync(new URL("../components/board/promotion-card.tsx", import.meta.url), "utf8");

test("frontend and backend board paths and payload fields stay aligned", () => {
  assert.match(api, /listPromotions: \(q = "", \{ cursor, limit = 10, signal \}/);
  assert.match(api, /\/api\/promociones\?\$\{params\}/);
  assert.match(api, /\/api\/promociones\/mias\?\$\{params\}/);
  assert.match(api, /createPromotion: \(data: \{ titulo: string; descripcion: string \}\)/);
  assert.match(api, /\/api\/promociones\/\$\{promotionId\}\/empresas-contratantes/);
  assert.match(api, /json: \{ empresa_id: companyId \}/);
  assert.match(api, /\/api\/solicitudes-contratacion-promocion\/\$\{requestId\}\/aceptar/);
  assert.match(api, /\/api\/solicitudes-contratacion-promocion\/\$\{requestId\}\/rechazar/);
  assert.doesNotMatch(api.match(/createPromotion:[^\n]+/)?.[0] ?? "", /usuario_id/);
  assert.match(api, /credentials: "include"/);
});

test("board actions keep controlled errors, cursor paging and inline confirmations", () => {
  assert.match(api, /if \("message" in body && typeof body\.message === "string"\)/);
  assert.match(api, /throw new ApiError\(response\.status/);
  for (const source of [boardPage, form, hiringModal, card]) assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(card, /\b(alert|confirm|prompt)\s*\(/);
  assert.match(boardPage, /boardApi\.listPromotions/);
  assert.match(boardPage, /boardApi\.getMyPromotions/);
  assert.match(boardPage, /loadingMore/);
  assert.match(boardPage, /knownIds/);
  assert.match(boardPage, /hasMore/);
  assert.match(boardPage, /boardApi\.rejectHiringRequest/);
  assert.match(card, /Confirmar aceptación/);
  assert.match(card, /Confirmar rechazo/);
  assert.match(card, /Contratado por/);
  assert.match(card, /disabled=\{busy\}/);
  assert.match(form, /maxLength=\{160\}/);
  assert.match(form, /maxLength=\{3000\}/);
  assert.match(hiringModal, /OWNER o RECRUITER/);
});
