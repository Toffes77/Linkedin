"use client";

import { FormEvent, useState } from "react";
import type { Post, User } from "@/lib/api";
import { postsApi } from "@/lib/api";
import { Avatar } from "@/components/common/avatar";
import { Alert } from "@/components/common/alert";
import { Icon } from "@/components/common/icons";

export function Composer({ user, onCreated }: { user: User; onCreated: (post: Post) => void }) {
  const [open, setOpen] = useState(false); const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); if (!text.trim()) return; setBusy(true); setError(""); try { const post = await postsApi.create(text.trim()); onCreated(post); setText(""); setOpen(false); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo publicar"); } finally { setBusy(false); } }
  return <section className="card composer">
    <div className="composer-top"><Avatar name={user.nombre} src={user.foto_perfil_url} size={48}/><button onClick={() => setOpen(true)} className="composer-trigger">Crear publicación</button></div>
    {open && <form onSubmit={submit} className="composer-form"><label htmlFor="post-text" className="sr-only">Contenido de la publicación</label><textarea id="post-text" autoFocus maxLength={3000} value={text} onChange={(e) => setText(e.target.value)} placeholder="¿Sobre qué querés hablar?" />{error && <Alert>{error}</Alert>}<div><span>{text.length}/3000</span><button type="button" onClick={() => setOpen(false)} className="text-button">Cancelar</button><button disabled={busy || !text.trim()} className="primary-button">{busy ? "Publicando..." : "Publicar"}</button></div></form>}
    {!open && <div className="composer-actions"><span><Icon name="video"/>Video</span><span><Icon name="image"/>Foto</span><span><Icon name="write"/>Escribir artículo</span></div>}
  </section>;
}
