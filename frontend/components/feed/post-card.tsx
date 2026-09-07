"use client";

import Link from "next/link";
import Image from "next/image";
import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { CommentsSection } from "@/components/feed/comments-section";
import { PostMediaGrid } from "@/components/feed/post-media-grid";
import { SharePostModal } from "@/components/feed/share-post-modal";
import { mediaUrl, postsApi, type FeedPost, type PostMedia, type PostMediaType, type ReactionCounts, type ReactionType, type User } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { MAX_POST_MEDIA_ITEMS } from "@/lib/post-media";
import { countsAfterReaction, countsAfterRemoval } from "@/lib/reaction-state";

const reactionLabels: Record<ReactionType, string> = { like: "Me gusta", celebrar: "Celebrar", apoyar: "Apoyar", interesante: "Interesante" };
type EditMedia = { key: string; kind: "existing"; media: PostMedia } | { key: string; kind: "new"; file: File; previewUrl: string; tipo: PostMediaType };

export function PostCard({ post, currentUser, onDelete, onUpdate, highlighted = false }: { post: FeedPost; currentUser: User; onDelete: (id: number) => void; onUpdate: (post: FeedPost) => void; highlighted?: boolean }) {
  const [counts, setCounts] = useState<ReactionCounts>(post.reacciones);
  const [reaction, setReaction] = useState<ReactionType | null>(post.mi_reaccion);
  const [commentCount, setCommentCount] = useState(post.cantidad_comentarios);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editMedia, setEditMedia] = useState<EditMedia[]>([]);
  const [text, setText] = useState(post.texto);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [shareOpen, setShareOpen] = useState(false);
  const [shareStatus, setShareStatus] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const editImageInputRef = useRef<HTMLInputElement>(null);
  const editVideoInputRef = useRef<HTMLInputElement>(null);
  const editUrlsRef = useRef(new Set<string>());
  const updateCommentCount = useCallback((count: number) => setCommentCount(count), []);

  useEffect(() => () => editUrlsRef.current.forEach((url) => URL.revokeObjectURL(url)), []);

  function clearEditUrls() {
    editUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    editUrlsRef.current.clear();
  }

  function beginEdit() {
    clearEditUrls();
    setText(post.texto);
    setEditMedia(post.multimedia.map((media) => ({ key: `existing-${media.id}`, kind: "existing", media })));
    setError("");
    setEditing(true);
    setMenu(false);
  }

  function cancelEdit() {
    clearEditUrls();
    setText(post.texto);
    setEditMedia([]);
    setError("");
    setEditing(false);
  }

  function addEditFiles(event: ChangeEvent<HTMLInputElement>, tipo: PostMediaType) {
    const incoming = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!incoming.length) return;
    if (editMedia.length + incoming.length > MAX_POST_MEDIA_ITEMS) {
      setError(`Podés conservar o agregar hasta ${MAX_POST_MEDIA_ITEMS} archivos.`);
      return;
    }
    const additions: EditMedia[] = incoming.map((file, index) => {
      const previewUrl = URL.createObjectURL(file);
      editUrlsRef.current.add(previewUrl);
      return { key: `new-${Date.now()}-${index}-${file.name}`, kind: "new", file, previewUrl, tipo };
    });
    setEditMedia((current) => [...current, ...additions]);
  }

  function removeEditMedia(key: string) {
    setEditMedia((current) => {
      const removed = current.find((item) => item.key === key);
      if (removed?.kind === "new") {
        URL.revokeObjectURL(removed.previewUrl);
        editUrlsRef.current.delete(removed.previewUrl);
      }
      return current.filter((item) => item.key !== key);
    });
  }

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
    if (!text.trim() && !editMedia.length) return;
    setBusy(true);
    setError("");
    try {
      const keptIds = editMedia.filter((item): item is Extract<EditMedia, { kind: "existing" }> => item.kind === "existing").map((item) => item.media.id);
      const files = editMedia.filter((item): item is Extract<EditMedia, { kind: "new" }> => item.kind === "new").map((item) => item.file);
      const updated = await postsApi.update(post.id, text.trim(), keptIds, files);
      onUpdate({ ...post, ...updated });
      clearEditUrls();
      setEditMedia([]);
      setEditing(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo editar");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError("");
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
      {post.autor_id === currentUser.id ? <div className="post-menu"><button type="button" onClick={() => setMenu(!menu)} aria-label="Opciones"><Icon name="more"/></button>{menu ? <div><button type="button" onClick={beginEdit}><Icon name="edit"/>Editar</button><button type="button" onClick={() => { setConfirmingDelete(true); setMenu(false); }}><Icon name="trash"/>Eliminar</button></div> : null}</div> : null}
    </header>
    {confirmingDelete ? <div className="post-delete-confirm" role="alert"><strong>¿Eliminar esta publicación?</strong><span>También se eliminará su multimedia.</span><div><button type="button" className="text-button" disabled={busy} onClick={() => setConfirmingDelete(false)}>Cancelar</button><button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>{busy ? "Eliminando..." : "Eliminar"}</button></div></div> : null}
    {editing ? <div className="post-edit">
      <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={3000}/>
      <input ref={editImageInputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => addEditFiles(event, "IMAGEN")}/>
      <input ref={editVideoInputRef} className="sr-only" type="file" accept="video/mp4,video/webm" multiple onChange={(event) => addEditFiles(event, "VIDEO")}/>
      <div className="composer-media-buttons"><button type="button" disabled={busy || editMedia.length >= MAX_POST_MEDIA_ITEMS} onClick={() => editImageInputRef.current?.click()}><Icon name="image"/>Foto</button><button type="button" disabled={busy || editMedia.length >= MAX_POST_MEDIA_ITEMS} onClick={() => editVideoInputRef.current?.click()}><Icon name="video"/>Video</button></div>
      {editMedia.length ? <div className="composer-previews">{editMedia.map((item, index) => { const source = item.kind === "existing" ? mediaUrl(item.media.ruta) ?? "" : item.previewUrl; const tipo = item.kind === "existing" ? item.media.tipo : item.tipo; return <div className="composer-preview" key={item.key}>{tipo === "IMAGEN" ? <Image unoptimized fill sizes="160px" src={source} alt={`Multimedia ${index + 1}`}/> : <video src={source} controls preload="metadata"/>}<button type="button" onClick={() => removeEditMedia(item.key)} disabled={busy} aria-label={`Quitar multimedia ${index + 1}`}>×</button></div>; })}</div> : null}
      <div className="post-edit-actions"><button type="button" onClick={cancelEdit} disabled={busy} className="text-button">Cancelar</button><button type="button" onClick={() => void save()} disabled={busy || (!text.trim() && !editMedia.length)} className="primary-button">{busy ? "Guardando..." : "Guardar"}</button></div>
    </div> : <>{post.texto ? <p className="post-text">{post.texto}</p> : null}<PostMediaGrid items={post.multimedia}/></>}
    <div className="post-summary">
      <span>👍 {reactionCount} reacciones</span>
      <button type="button" onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}>{commentCount} {commentCount === 1 ? "comentario" : "comentarios"}</button>
    </div>
    {error ? <p className="inline-error" role="alert">{error}</p> : null}
    {shareStatus ? <p className="post-share-status" role="status">{shareStatus}</p> : null}
    <footer>
      <div className="reaction-picker"><button type="button" disabled={busy} className={reaction ? "selected" : ""}><Icon name="like"/>{reaction ? reactionLabels[reaction] : "Reaccionar"}</button><div>{(Object.keys(reactionLabels) as ReactionType[]).map((type) => <button type="button" disabled={busy} key={type} title={reactionLabels[type]} onClick={() => void react(type)}>{type === "like" ? "👍" : type === "celebrar" ? "👏" : type === "apoyar" ? "❤️" : "💡"}</button>)}</div></div>
      <button type="button" className={commentsOpen ? "selected" : ""} onClick={() => setCommentsOpen((open) => !open)} aria-expanded={commentsOpen}><Icon name="comment"/>Comentar</button>
      <button type="button" onClick={() => { setShareStatus(""); setShareOpen(true); }}><Icon name="send"/>Enviar</button>
    </footer>
    <CommentsSection postId={post.id} currentUser={currentUser} open={commentsOpen} onCountChange={updateCommentCount}/>
    {shareOpen ? <SharePostModal post={post} onClose={() => setShareOpen(false)} onSent={(contactName) => { setShareOpen(false); setShareStatus(`Publicación enviada a ${contactName}.`); }}/> : null}
  </article>;
}
