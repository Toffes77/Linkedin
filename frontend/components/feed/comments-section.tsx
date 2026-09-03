"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CommentForm } from "@/components/feed/comment-form";
import { CommentItem } from "@/components/feed/comment-item";
import { commentsApi, type Comment, type User } from "@/lib/api";
import { buildVisibleCommentRows, mergeCommentPage, type CommentChildrenPage } from "@/lib/comment-pagination";

export function CommentsSection({ postId, currentUser, open, onCountChange }: { postId: number; currentUser: User; open: boolean; onCountChange: (count: number) => void }) {
  const [roots, setRoots] = useState<Comment[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  const [children, setChildren] = useState<Record<number, CommentChildrenPage>>({});

  async function refreshCount() { const { cantidad } = await commentsApi.count(postId); onCountChange(cantidad); }

  const loadRoots = useCallback(async (cursor: string | null, append: boolean) => {
    setLoading(true);
    try {
      const page = await commentsApi.list(postId, cursor);
      setRoots((current) => append ? [...(current ?? []), ...page.items] : page.items);
      setNextCursor(page.next_cursor); setHasMore(page.has_more); setLoadError("");
    } catch (reason) { setLoadError(reason instanceof Error ? reason.message : "No se pudieron cargar los comentarios."); }
    finally { setLoading(false); }
  }, [postId]);

  useEffect(() => { if (open && roots === null) void loadRoots(null, false); }, [loadRoots, open, roots]);

  function updateComment(commentId: number, update: (comment: Comment) => Comment) {
    setRoots((current) => current?.map((item) => item.id === commentId ? update(item) : item) ?? null);
    setChildren((current) => Object.fromEntries(Object.entries(current).map(([key, page]) => [key, { ...page, items: page.items.map((item) => item.id === commentId ? update(item) : item) }])));
  }

  async function loadReplies(parentId: number, cursor: string | null, append: boolean) {
    setChildren((current) => ({ ...current, [parentId]: { items: current[parentId]?.items ?? [], nextCursor: current[parentId]?.nextCursor ?? null, hasMore: current[parentId]?.hasMore ?? false, loading: true, error: "" } }));
    try {
      const page = await commentsApi.replies(parentId, cursor);
      setChildren((current) => ({ ...current, [parentId]: { items: append ? mergeCommentPage(current[parentId]?.items ?? [], page.items) : page.items, nextCursor: page.next_cursor, hasMore: page.has_more, loading: false, error: "" } }));
    } catch (reason) {
      setChildren((current) => ({ ...current, [parentId]: { ...(current[parentId] ?? { items: [], nextCursor: null, hasMore: false }), loading: false, error: reason instanceof Error ? reason.message : "No se pudieron cargar las respuestas." } }));
    }
  }

  function toggleReplies(commentId: number) {
    const opening = !openIds.has(commentId);
    setOpenIds((current) => { const next = new Set(current); if (opening) next.add(commentId); else next.delete(commentId); return next; });
    if (opening && !children[commentId]) void loadReplies(commentId, null, false);
  }

  async function create(content: string) { const created = await commentsApi.create(postId, content); setRoots((current) => [created, ...(current ?? [])]); await refreshCount(); }

  async function reply(parent: Comment, content: string) {
    const created = await commentsApi.reply(parent.id, content);
    updateComment(parent.id, (comment) => ({ ...comment, cantidad_respuestas: comment.cantidad_respuestas + 1 }));
    setOpenIds((current) => new Set(current).add(parent.id));
    setChildren((current) => ({ ...current, [parent.id]: { items: mergeCommentPage(current[parent.id]?.items ?? [], [created]), nextCursor: current[parent.id]?.nextCursor ?? null, hasMore: current[parent.id]?.hasMore ?? parent.cantidad_respuestas > 0, loading: false, error: "" } }));
    await refreshCount();
  }

  async function remove(comment: Comment) {
    setActionError("");
    try {
      await commentsApi.delete(comment.id);
      setRoots((current) => current?.filter((item) => item.id !== comment.id) ?? null);
      setChildren((current) => {
        const next = { ...current }; const pending = [comment.id];
        while (pending.length) { const id = pending.pop()!; next[id]?.items.forEach((child) => pending.push(child.id)); delete next[id]; }
        for (const [key, page] of Object.entries(next)) next[Number(key)] = { ...page, items: page.items.filter((item) => item.id !== comment.id) };
        return next;
      });
      if (comment.comentario_padre_id !== null) updateComment(comment.comentario_padre_id, (parent) => ({ ...parent, cantidad_respuestas: Math.max(0, parent.cantidad_respuestas - 1) }));
      setOpenIds((current) => { const next = new Set(current); next.delete(comment.id); return next; });
      await refreshCount();
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : "No se pudo eliminar el comentario."); }
  }

  const visibleRows = useMemo(() => buildVisibleCommentRows(roots ?? [], openIds, children), [children, openIds, roots]);
  if (!open) return null;

  return <section className="comments-section" aria-label="Comentarios de la publicación">
    <CommentForm currentUser={currentUser} placeholder="Añade un comentario..." submitLabel="Comentar" disabled={loading || Boolean(loadError)} onSubmit={create}/>
    {actionError && <p className="comments-action-error inline-error" role="alert">{actionError}</p>}
    <div className="comments-scroll">
      {loading && roots === null && <p className="comments-state">Cargando comentarios...</p>}
      {loadError && <p className="comments-state inline-error" role="alert">{loadError}</p>}
      {!loading && !loadError && roots?.length === 0 && <p className="comments-state">Sé la primera persona en comentar.</p>}
      {visibleRows.map((row) => row.kind === "comment" ? <CommentItem key={`comment-${row.comment.id}`} comment={row.comment} depth={row.depth} currentUser={currentUser} replying={replyingTo === row.comment.id} responsesOpen={openIds.has(row.comment.id)} onReplyingChange={(replying) => setReplyingTo(replying ? row.comment.id : null)} onReply={(content) => reply(row.comment, content)} onDelete={() => remove(row.comment)} onToggleResponses={() => toggleReplies(row.comment.id)}/> : <div key={`control-${row.parentId}`} className="comments-state" style={{ marginLeft: `${Math.min(row.depth, 6) * 18}px` }}>
        {children[row.parentId]?.loading && <span>Cargando respuestas...</span>}
        {children[row.parentId]?.error && <button type="button" className="text-button" onClick={() => void loadReplies(row.parentId, null, false)}>Reintentar respuestas</button>}
        {children[row.parentId]?.hasMore && !children[row.parentId]?.loading && <button type="button" className="text-button" onClick={() => void loadReplies(row.parentId, children[row.parentId].nextCursor, true)}>Ver más respuestas</button>}
      </div>)}
      {hasMore && !loading && <button type="button" className="secondary-button" onClick={() => void loadRoots(nextCursor, true)}>Ver más comentarios</button>}
      {loading && roots !== null && <p className="comments-state">Cargando más comentarios...</p>}
    </div>
  </section>;
}
