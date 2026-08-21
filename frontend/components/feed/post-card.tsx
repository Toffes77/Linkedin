"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { postsApi, type Post, type ReactionCounts, type ReactionType, type User } from "@/lib/api";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { formatDate } from "@/lib/format";

const reactionLabels: Record<ReactionType, string> = { like: "Me gusta", celebrar: "Celebrar", apoyar: "Apoyar", interesante: "Interesante" };

export function PostCard({ post, author, currentUser, onDelete, onUpdate }: { post: Post; author?: User; currentUser: User; onDelete: (id: number) => void; onUpdate: (post: Post) => void }) {
  const [counts, setCounts] = useState<ReactionCounts | null>(null); const [reaction, setReaction] = useState<ReactionType | null>(null); const [menu, setMenu] = useState(false); const [editing, setEditing] = useState(false); const [text, setText] = useState(post.texto); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { postsApi.reactionCounts(post.id).then(setCounts).catch(() => setCounts(null)); }, [post.id]);
  async function react(tipo: ReactionType) { setBusy(true); setError(""); try { if (reaction) await postsApi.changeReaction(post.id, tipo); else await postsApi.react(currentUser.id, post.id, tipo); setCounts((old) => old ? { ...old, ...(reaction ? { [reaction]: Math.max(0, old[reaction] - 1) } : {}), [tipo]: old[tipo] + (reaction === tipo ? 0 : 1) } : old); setReaction(tipo); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo reaccionar"); } finally { setBusy(false); } }
  async function save() { setBusy(true); try { const updated = await postsApi.update(post.id, text.trim()); onUpdate(updated); setEditing(false); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo editar"); } finally { setBusy(false); } }
  async function remove() { if (!confirm("¿Eliminar esta publicación?")) return; setBusy(true); try { await postsApi.delete(post.id); onDelete(post.id); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo eliminar"); setBusy(false); } }
  const name = author?.nombre ?? `Usuario ${post.autor_id}`;
  return <article className="card post-card">
    <header><Link href={`/perfil/${post.autor_id}`}><Avatar name={name} src={author?.foto_perfil_url} size={48}/></Link><div><Link href={`/perfil/${post.autor_id}`}><strong>{name}</strong></Link><span>{author?.headline ?? "Profesional de la red"}</span><small>{formatDate(post.fecha)}</small></div>{post.autor_id === currentUser.id && <div className="post-menu"><button onClick={() => setMenu(!menu)} aria-label="Opciones"><Icon name="more"/></button>{menu && <div><button onClick={() => { setEditing(true); setMenu(false); }}><Icon name="edit"/>Editar</button><button onClick={remove}><Icon name="trash"/>Eliminar</button></div>}</div>}</header>
    {editing ? <div className="post-edit"><textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={3000}/><button onClick={() => setEditing(false)} className="text-button">Cancelar</button><button onClick={save} disabled={busy || !text.trim()} className="primary-button">Guardar</button></div> : <p className="post-text">{post.texto}</p>}
    {counts && <div className="reaction-summary"><span>👍</span>{Object.values(counts).reduce((a, b) => a + b, 0)} reacciones</div>}
    {error && <p className="inline-error">{error}</p>}
    <footer><div className="reaction-picker"><button disabled={busy} className={reaction ? "selected" : ""}><Icon name="like"/>{reaction ? reactionLabels[reaction] : "Recomendar"}</button><div>{(Object.keys(reactionLabels) as ReactionType[]).map((type) => <button key={type} title={reactionLabels[type]} onClick={() => react(type)}>{type === "like" ? "👍" : type === "celebrar" ? "👏" : type === "apoyar" ? "❤️" : "💡"}</button>)}</div></div><button><Icon name="send"/>Enviar</button></footer>
  </article>;
}
