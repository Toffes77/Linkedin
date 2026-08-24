"use client";

import { useState, type FormEvent } from "react";
import { Avatar } from "@/components/common/avatar";
import { type User } from "@/lib/api";

export function CommentForm({ currentUser, placeholder, submitLabel, compact = false, disabled = false, onSubmit }: { currentUser: User; placeholder: string; submitLabel: string; compact?: boolean; disabled?: boolean; onSubmit: (content: string) => Promise<void> }) {
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || busy || disabled) return;
    setBusy(true);
    setError("");
    try {
      await onSubmit(trimmed);
      setContent("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo publicar el comentario.");
    } finally {
      setBusy(false);
    }
  }

  return <form className={`comment-form${compact ? " compact" : ""}`} onSubmit={submit}>
    <Avatar name={currentUser.nombre} src={currentUser.foto_perfil_url} size={compact ? 28 : 36}/>
    <div className="comment-form-body">
      <textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder={placeholder} maxLength={1000} rows={1} aria-label={placeholder} disabled={disabled}/>
      {content.trim() && <button className="primary-button comment-submit" disabled={disabled || busy || !content.trim()}>{busy ? "Publicando..." : submitLabel}</button>}
      {error && <p className="inline-error" role="alert">{error}</p>}
    </div>
  </form>;
}
