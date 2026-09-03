"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { CommentsSection } from "@/components/feed/comments-section";
import { SharePostModal } from "@/components/feed/share-post-modal";
import { postsApi, type FeedPost, type ReactionCounts, type ReactionType, type User } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { countsAfterReaction, countsAfterRemoval } from "@/lib/reaction-state";

const reactionLabels: Record<ReactionType, string> = { like: "Me gusta", celebrar: "Celebrar", apoyar: "Apoyar", interesante: "Interesante" };

export function PostCard({ post, currentUser, onDelete, onUpdate, highlighted = false }: { post: FeedPost; currentUser: User; onDelete: (id: number) => void; onUpdate: (post: FeedPost) => void; highlighted?: boolean }) {
  const [counts, setCounts] = useState<ReactionCounts>(post.reacciones);
  const [reaction, setReaction] = useState<ReactionType | null>(post.mi_reaccion);
  const [commentCount, setCommentCount] = useState(post.cantidad_comentarios);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(post.texto);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [shareOpen, setShareOpen] = useState(false);
  const [shareStatus, setShareStatus] = useState("");
  const updateCommentCount = useCallback((count: number) => setCommentCount(count), []);

  async function react(tipo: ReactionType) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (reaction === tipo) {
        await postsApi.removeReaction(post.id);
        setCounts((old) => countsAfterRemoval(old, reaction)!);
        setReaction(null);
        return;
      }
      if (reaction) await postsApi.changeReaction(post.id, tipo);
      else await postsApi.react(post.id, tipo);
      setCounts((old) => countsAfterReaction(old, reaction, tipo)!);
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
      onUpdate({ ...post, ...updated });
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

  const name = post.autor.nombre;
  const reactionCount = Object.values(counts).reduce((a, b) => a + b, 0);
  return <article className={`card post-card${highlighted ? " shared-post-highlight" : ""}`}>
    {highlighted ? <p className="shared-post-label">Publicación compartida</p> : null}
    <header>
      <Link href={`/perfil/${post.autor_id}`}><Avatar name={name} src={post.autor.foto_perfil_url} size={48}/></Link>
      <div><Link href={`/perfil/${post.autor_id}`}><strong>{name}</strong></Link><span>{post.autor.headline}</span><small>{formatDate(post.fecha)}</small></div>
      {post.autor_id === currentUser.id && <div className="post-menu"><button onClick={() => setMenu(!menu)} aria-label="Opciones"><Icon name="more"/></button>{menu && <div><button onClick={() => { setEditing(true); setMenu(false); }}><Icon name="edit"/>Editar</button><button onClick={remove}><Icon name="trash"/>Eliminar</button></div>}</div>}
    </header>
    {editing ? <div className="post-edit"><textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={3000}/><button onClick={() => setEditing(false)} className="text-button">Cancelar</button><button onClick={save} disabled={busy || !text.trim()} className="primary-button">Guardar</button></div> : <p className="post-text">{post.texto}</p>}
    <div className="post-summary">
      <span>👍 {reactionCount} reacciones</span>
      <button type="button" onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}>{commentCount} {commentCount === 1 ? "comentario" : "comentarios"}</button>
    </div>
    {error && <p className="inline-error">{error}</p>}
    {shareStatus ? <p className="post-share-status" role="status">{shareStatus}</p> : null}
    <footer>
      <div className="reaction-picker"><button disabled={busy} className={reaction ? "selected" : ""}><Icon name="like"/>{reaction ? reactionLabels[reaction] : "Reaccionar"}</button><div>{(Object.keys(reactionLabels) as ReactionType[]).map((type) => <button disabled={busy} key={type} title={reactionLabels[type]} onClick={() => react(type)}>{type === "like" ? "👍" : type === "celebrar" ? "👏" : type === "apoyar" ? "❤️" : "💡"}</button>)}</div></div>
      <button type="button" className={commentsOpen ? "selected" : ""} onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}><Icon name="comment"/>Comentar</button>
      <button type="button" onClick={() => { setShareStatus(""); setShareOpen(true); }}><Icon name="send"/>Enviar</button>
    </footer>
    <CommentsSection postId={post.id} currentUser={currentUser} open={commentsOpen} onCountChange={updateCommentCount}/>
    {shareOpen ? <SharePostModal post={post} onClose={() => setShareOpen(false)} onSent={(contactName) => { setShareOpen(false); setShareStatus(`Publicación enviada a ${contactName}.`); }}/> : null}
  </article>;
}
