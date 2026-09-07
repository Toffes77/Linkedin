"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { Post, PostMediaType, User } from "@/lib/api";
import { postsApi } from "@/lib/api";
import { MAX_POST_MEDIA_ITEMS } from "@/lib/post-media";
import { Avatar } from "@/components/common/avatar";
import { Alert } from "@/components/common/alert";
import { Icon } from "@/components/common/icons";

type SelectedFile = { key: string; file: File; previewUrl: string; tipo: PostMediaType };

export function Composer({ user, onCreated }: { user: User; onCreated: (post: Post) => void }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<SelectedFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const previewUrlsRef = useRef(new Set<string>());

  useEffect(() => () => {
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  function clearSelection() {
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    previewUrlsRef.current.clear();
    setSelected([]);
    if (imageInputRef.current) imageInputRef.current.value = "";
    if (videoInputRef.current) videoInputRef.current.value = "";
  }

  function closeComposer() {
    if (busy) return;
    clearSelection();
    setText("");
    setError("");
    setOpen(false);
  }

  function choose(kind: "image" | "video") {
    setOpen(true);
    setError("");
    (kind === "image" ? imageInputRef : videoInputRef).current?.click();
  }

  function addFiles(event: ChangeEvent<HTMLInputElement>, tipo: PostMediaType) {
    const incoming = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!incoming.length) return;
    if (selected.length + incoming.length > MAX_POST_MEDIA_ITEMS) {
      setError(`Podés agregar hasta ${MAX_POST_MEDIA_ITEMS} archivos por publicación.`);
      return;
    }
    const additions = incoming.map((file, index) => {
      const previewUrl = URL.createObjectURL(file);
      previewUrlsRef.current.add(previewUrl);
      return { key: `${Date.now()}-${index}-${file.name}`, file, previewUrl, tipo };
    });
    setSelected((current) => [...current, ...additions]);
  }

  function removeFile(key: string) {
    setSelected((current) => {
      const removed = current.find((item) => item.key === key);
      if (removed) {
        URL.revokeObjectURL(removed.previewUrl);
        previewUrlsRef.current.delete(removed.previewUrl);
      }
      return current.filter((item) => item.key !== key);
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() && !selected.length) return;
    setBusy(true);
    setError("");
    try {
      const post = await postsApi.create(text.trim(), selected.map((item) => item.file));
      onCreated(post);
      clearSelection();
      setText("");
      setOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo publicar");
    } finally {
      setBusy(false);
    }
  }

  return <section className="card composer">
    <input ref={imageInputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => addFiles(event, "IMAGEN")} aria-label="Seleccionar imágenes"/>
    <input ref={videoInputRef} className="sr-only" type="file" accept="video/mp4,video/webm" multiple onChange={(event) => addFiles(event, "VIDEO")} aria-label="Seleccionar videos"/>
    <div className="composer-top"><Avatar name={user.nombre} src={user.foto_perfil_url} size={48}/><button type="button" onClick={() => setOpen(true)} className="composer-trigger">Crear publicación</button></div>
    {open ? <form onSubmit={submit} className="composer-form">
      <label htmlFor="post-text" className="sr-only">Contenido de la publicación</label>
      <textarea id="post-text" autoFocus maxLength={3000} value={text} onChange={(event) => setText(event.target.value)} placeholder="¿Sobre qué querés hablar?"/>
      <div className="composer-media-buttons"><button type="button" onClick={() => choose("image")} disabled={busy || selected.length >= MAX_POST_MEDIA_ITEMS}><Icon name="image"/>Foto</button><button type="button" onClick={() => choose("video")} disabled={busy || selected.length >= MAX_POST_MEDIA_ITEMS}><Icon name="video"/>Video</button></div>
      {selected.length ? <div className="composer-previews" aria-label="Multimedia seleccionado">{selected.map((item, index) => <div className="composer-preview" key={item.key}>{item.tipo === "IMAGEN" ? <Image unoptimized fill sizes="160px" src={item.previewUrl} alt={`Vista previa ${index + 1}`}/> : <video src={item.previewUrl} controls preload="metadata"/>}<button type="button" onClick={() => removeFile(item.key)} disabled={busy} aria-label={`Quitar archivo ${index + 1}`}>×</button></div>)}</div> : null}
      {error ? <Alert>{error}</Alert> : null}
      <div className="composer-submit"><span>{text.length}/3000 · {selected.length}/{MAX_POST_MEDIA_ITEMS} archivos</span><button type="button" onClick={closeComposer} disabled={busy} className="text-button">Cancelar</button><button disabled={busy || (!text.trim() && !selected.length)} className="primary-button">{busy ? "Publicando..." : "Publicar"}</button></div>
    </form> : <div className="composer-actions"><button type="button" onClick={() => choose("video")}><Icon name="video"/>Video</button><button type="button" onClick={() => choose("image")}><Icon name="image"/>Foto</button><button type="button" onClick={() => setOpen(true)}><Icon name="write"/>Escribir artículo</button></div>}
  </section>;
}
