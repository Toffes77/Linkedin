import assert from "node:assert/strict";
import test from "node:test";
import { buildVisibleCommentRows, mergeCommentPage, type CommentChildrenPage } from "./comment-pagination.ts";
import type { Comment } from "./api.ts";

function comment(id: number, parent: number | null = null): Comment {
  return { id, publicacion_id: 1, usuario_id: 1, contenido: `Comment ${id}`, fecha: new Date(id * 1000).toISOString(), comentario_padre_id: parent, autor: { id: 1, nombre: "User", headline: null, foto_perfil_url: null }, cantidad_respuestas: 0 };
}

function page(items: Comment[]): CommentChildrenPage {
  return { items, nextCursor: null, hasMore: false, loading: false, error: "" };
}

test("replies are absent until their direct parent is expanded", () => {
  const roots = [comment(1)];
  const children = { 1: page([comment(2, 1)]) };
  assert.deepEqual(buildVisibleCommentRows(roots, new Set(), children).filter((row) => row.kind === "comment").map((row) => row.comment.id), [1]);
  assert.deepEqual(buildVisibleCommentRows(roots, new Set([1]), children).filter((row) => row.kind === "comment").map((row) => row.comment.id), [1, 2]);
});

test("loading more merges pages without duplicates and keeps total order", () => {
  assert.deepEqual(mergeCommentPage([comment(2), comment(4)], [comment(3), comment(4)]).map((item) => item.id), [2, 3, 4]);
});

test("a deeply expanded tree is flattened iteratively", () => {
  const depth = 5000;
  const children: Record<number, CommentChildrenPage> = {};
  const open = new Set<number>();
  for (let id = 1; id < depth; id += 1) { children[id] = page([comment(id + 1, id)]); open.add(id); }
  const rows = buildVisibleCommentRows([comment(1)], open, children);
  assert.equal(rows.filter((row) => row.kind === "comment").length, depth);
});
