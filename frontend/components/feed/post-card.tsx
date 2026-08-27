"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { CommentsSection } from "@/components/feed/comments-section";
import { SharePostModal } from "@/components/feed/share-post-modal";
import { commentsApi, postsApi, type Post, type ReactionCounts, type ReactionType, type User } from "@/lib/api";
import { formatDate } from "@/lib/format";

const reactionLabels: Record<ReactionType, string> = { like: "Me gusta", celebrar: "Celebrar", apoyar: "Apoyar", interesante: "Interesante" };

export function PostCard({ post, author, currentUser, onDelete, onUpdate, highlighted = false }: { post: Post; author?: User; currentUser: User; onDelete: (id: number) => void; onUpdate: (post: Post) => void; highlighted?: boolean }) {
  const [counts, setCounts] = useState<ReactionCounts | null>(null);
  const [reaction, setReaction] = useState<ReactionType | null>(null);
  const [commentCount, setCommentCount] = useState<number | null>(null);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(post.texto);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [shareOpen, setShareOpen] = useState(false);
  const [shareStatus, setShareStatus] = useState("");
  const updateCommentCount = useCallback((count: number) => setCommentCount(count), []);

  useEffect(() => {
    postsApi.reactionCounts(post.id).then(setCounts).catch(() => setCounts(null));
    commentsApi.count(post.id).then(({ cantidad }) => setCommentCount(cantidad)).catch(() => setCommentCount(null));
  }, [post.id]);

  async function react(tipo: ReactionType) {
    setBusy(true);
    setError("");
    try {
      if (reaction) await postsApi.changeReaction(post.id, tipo);
      else await postsApi.react(currentUser.id, post.id, tipo);
      setCounts((old) => old ? { ...old, ...(reaction ? { [reaction]: Math.max(0, old[reaction] - 1) } : {}), [tipo]: old[tipo] + (reaction === tipo ? 0 : 1) } : old);
      setReaction(tipo);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo reaccionar");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    try {
      const updated = await postsApi.update(post.id, text.trim());
      onUpdate(updated);
      setEditing(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo editar");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm("¿Eliminar esta publicación?")) return;
    setBusy(true);
    try {
      await postsApi.delete(post.id);
      onDelete(post.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo eliminar");
      setBusy(false);
    }
  }

  const name = author?.nombre ?? `Usuario ${post.autor_id}`;
  const reactionCount = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : null;
  return <article className={`card post-card${highlighted ? " shared-post-highlight" : ""}`}>
    {highlighted ? <p className="shared-post-label">Publicación compartida</p> : null}
    <header>
      <Link href={`/perfil/${post.autor_id}`}><Avatar name={name} src={author?.foto_perfil_url} size={48}/></Link>
      <div><Link href={`/perfil/${post.autor_id}`}><strong>{name}</strong></Link><span>{author?.headline ?? "Profesional de la red"}</span><small>{formatDate(post.fecha)}</small></div>
      {post.autor_id === currentUser.id && <div className="post-menu"><button onClick={() => setMenu(!menu)} aria-label="Opciones"><Icon name="more"/></button>{menu && <div><button onClick={() => { setEditing(true); setMenu(false); }}><Icon name="edit"/>Editar</button><button onClick={remove}><Icon name="trash"/>Eliminar</button></div>}</div>}
    </header>
    {editing ? <div className="post-edit"><textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={3000}/><button onClick={() => setEditing(false)} className="text-button">Cancelar</button><button onClick={save} disabled={busy || !text.trim()} className="primary-button">Guardar</button></div> : <p className="post-text">{post.texto}</p>}
    {(reactionCount !== null || commentCount !== null) && <div className="post-summary">
      <span>{reactionCount !== null && <>👍 {reactionCount} reacciones</>}</span>
      {commentCount !== null && <button type="button" onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}>{commentCount} {commentCount === 1 ? "comentario" : "comentarios"}</button>}
    </div>}
    {error && <p className="inline-error">{error}</p>}
    {shareStatus ? <p className="post-share-status" role="status">{shareStatus}</p> : null}
    <footer>
      <div className="reaction-picker"><button disabled={busy} className={reaction ? "selected" : ""}><Icon name="like"/>{reaction ? reactionLabels[reaction] : "Reaccionar"}</button><div>{(Object.keys(reactionLabels) as ReactionType[]).map((type) => <button key={type} title={reactionLabels[type]} onClick={() => react(type)}>{type === "like" ? "👍" : type === "celebrar" ? "👏" : type === "apoyar" ? "❤️" : "💡"}</button>)}</div></div>
      <button type="button" className={commentsOpen ? "selected" : ""} onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}><Icon name="comment"/>Comentar</button>
      <button type="button" onClick={() => { setShareStatus(""); setShareOpen(true); }}><Icon name="send"/>Enviar</button>
    </footer>
    <CommentsSection postId={post.id} currentUser={currentUser} open={commentsOpen} onCountChange={updateCommentCount}/>
    {shareOpen ? <SharePostModal post={post} onClose={() => setShareOpen(false)} onSent={(contactName) => { setShareOpen(false); setShareStatus(`Publicación enviada a ${contactName}.`); }}/> : null}
  </article>;
}
