"use client";

import { useEffect, useState } from "react";
import { CommentForm } from "@/components/feed/comment-form";
import { CommentItem } from "@/components/feed/comment-item";
import { commentsApi, type Comment, type User } from "@/lib/api";

function totalComments(comments: Comment[]): number {
  return comments.reduce((total, comment) => total + 1 + totalComments(comment.respuestas), 0);
}

function appendReply(comments: Comment[], reply: Comment): Comment[] {
  let changed = false;
  const updated = comments.map((comment) => {
    if (comment.id === reply.comentario_padre_id) {
      changed = true;
      const responses = [...comment.respuestas, reply];
      return { ...comment, respuestas: responses, cantidad_respuestas: responses.length };
    }
    const responses = appendReply(comment.respuestas, reply);
    if (responses === comment.respuestas) return comment;
    changed = true;
    return { ...comment, respuestas: responses };
  });
  return changed ? updated : comments;
}

function removeFromTree(comments: Comment[], commentId: number): Comment[] {
  const remaining = comments.filter((comment) => comment.id !== commentId);
  if (remaining.length !== comments.length) return remaining;

  let changed = false;
  const updated = comments.map((comment) => {
    const responses = removeFromTree(comment.respuestas, commentId);
    if (responses === comment.respuestas) return comment;
    changed = true;
    return { ...comment, respuestas: responses, cantidad_respuestas: responses.length };
  });
  return changed ? updated : comments;
}

export function CommentsSection({ postId, currentUser, open, onCountChange }: { postId: number; currentUser: User; open: boolean; onCountChange: (count: number) => void }) {
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [replyingTo, setReplyingTo] = useState<number | null>(null);

  useEffect(() => {
    if (!open || comments !== null) return;
    let cancelled = false;
    commentsApi.list(postId).then((items) => {
      if (cancelled) return;
      setComments(items);
      setLoading(false);
    }).catch((reason) => {
      if (cancelled) return;
      setLoadError(reason instanceof Error ? reason.message : "No se pudieron cargar los comentarios.");
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [comments, open, postId]);

  useEffect(() => {
    if (comments !== null) onCountChange(totalComments(comments));
  }, [comments, onCountChange]);

  if (!open) return null;

  async function create(content: string) {
    const created = await commentsApi.create(postId, content);
    setComments((current) => {
      return [created, ...(current ?? [])];
    });
  }

  async function reply(commentId: number, content: string) {
    const created = await commentsApi.reply(commentId, content);
    setComments((current) => {
      return appendReply(current ?? [], created);
    });
  }

  async function remove(comment: Comment) {
    setActionError("");
    try {
      await commentsApi.delete(comment.id);
      setComments((current) => {
        return removeFromTree(current ?? [], comment.id);
      });
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "No se pudo eliminar el comentario.");
    }
  }

  return <section className="comments-section" aria-label="Comentarios de la publicación">
    <CommentForm currentUser={currentUser} placeholder="Añade un comentario..." submitLabel="Comentar" disabled={loading || Boolean(loadError)} onSubmit={create}/>
    {actionError && <p className="comments-action-error inline-error" role="alert">{actionError}</p>}
    <div className="comments-scroll">
      {loading && <p className="comments-state">Cargando comentarios...</p>}
      {loadError && <p className="comments-state inline-error" role="alert">{loadError}</p>}
      {!loading && !loadError && comments?.length === 0 && <p className="comments-state">Sé la primera persona en comentar.</p>}
      {comments?.map((comment) => <CommentItem key={comment.id} comment={comment} currentUser={currentUser} replyingTo={replyingTo} setReplyingTo={setReplyingTo} onReply={reply} onDelete={remove}/>) }
    </div>
  </section>;
}
