"use client";

import Link from "next/link";
import { CSSProperties, FormEvent, KeyboardEvent, useEffect, useRef } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import type { MessageContact, PrivateMessage } from "@/lib/api";

function messageTime(value: string) {
  return new Intl.DateTimeFormat("es-AR", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function ChatWindow({
  contact,
  currentUserId,
  messages,
  draft,
  minimized,
  busy,
  error,
  canLoadPrevious,
  onDraftChange,
  onSend,
  onLoadPrevious,
  onMinimize,
  onClose,
  backgroundColor,
  backgroundImageUrl,
  messageFontFamily,
}: {
  contact: MessageContact;
  currentUserId: number;
  messages: PrivateMessage[];
  draft: string;
  minimized: boolean;
  busy: boolean;
  error: string | null;
  canLoadPrevious: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onLoadPrevious: () => void;
  onMinimize: () => void;
  onClose: () => void;
  backgroundColor: string;
  backgroundImageUrl: string | null;
  messageFontFamily: string;
}) {
  const historyRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!minimized) historyRef.current?.scrollTo({ top: historyRef.current.scrollHeight });
  }, [messages.length, minimized, contact.usuario_id]);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSend();
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  }

  const chatStyle = { "--message-font-family": messageFontFamily } as CSSProperties;
  const historyStyle: CSSProperties = {
    backgroundColor,
    backgroundImage: backgroundImageUrl
      ? `linear-gradient(#ffffff24, #ffffff24), url(${backgroundImageUrl})`
      : undefined,
  };

  return <section className={`message-chat-window${minimized ? " minimized" : ""}`} style={chatStyle} aria-label={`Conversación con ${contact.nombre}`}>
    <header className="message-chat-header">
      <button type="button" className="message-chat-identity" onClick={minimized ? onMinimize : undefined}>
        <Avatar name={contact.nombre} src={contact.foto_perfil_url} size={34}/>
        <span><strong>{contact.nombre}</strong><small>{contact.headline}</small></span>
      </button>
      <div className="message-header-actions">
        <button type="button" onClick={onMinimize} aria-label={minimized ? "Restaurar chat" : "Minimizar chat"}>{minimized ? "⌃" : "—"}</button>
        <button type="button" onClick={onClose} aria-label="Cerrar chat">×</button>
      </div>
    </header>
    {!minimized ? <>
      <div className={`message-history${backgroundImageUrl ? " custom-background" : ""}`} ref={historyRef} style={historyStyle}>
        {canLoadPrevious ? <button type="button" className="message-load-previous" onClick={onLoadPrevious}>Cargar mensajes anteriores</button> : null}
        {messages.length === 0 ? <div className="message-empty-chat"><Avatar name={contact.nombre} src={contact.foto_perfil_url} size={64}/><strong>{contact.nombre}</strong><span>Este es el comienzo de la conversación.</span></div> : null}
        {messages.map((message) => <div className={`message-bubble-row${message.autor_id === currentUserId ? " own" : ""}`} key={message.id}>
          {message.autor_id !== currentUserId ? <Avatar name={contact.nombre} src={contact.foto_perfil_url} size={30}/> : null}
          <div className={`message-bubble${message.tipo === "PUBLICACION" ? " shared-post-message" : ""}`}>
            {message.tipo === "PUBLICACION" ? message.publicacion ? <Link href={`/feed?publicacion=${message.publicacion.id}`} className="shared-post-message-card">
              <span className="shared-post-message-author"><Avatar name={message.publicacion.autor_nombre} src={message.publicacion.autor_foto_perfil_url} size={32}/><span><strong>Publicación de {message.publicacion.autor_nombre}</strong><small>{message.publicacion.autor_headline}</small></span></span>
              <span className="shared-post-message-excerpt">{message.publicacion.texto}</span>
              <span className="shared-post-message-link">Ver publicación</span>
            </Link> : <p className="shared-post-unavailable">Esta publicación ya no está disponible.</p> : <p>{message.contenido}</p>}
            <time>{messageTime(message.fecha)}</time>
          </div>
        </div>)}
      </div>
      <form className="message-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor={`message-draft-${contact.usuario_id}`}>Escribir mensaje</label>
        <textarea
          id={`message-draft-${contact.usuario_id}`}
          value={draft}
          maxLength={2000}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={keyDown}
          placeholder="Escribir un mensaje..."
          rows={2}
        />
        <div>
          <span>{draft.length}/2000</span>
          <button type="submit" disabled={busy || !draft.trim()} aria-label="Enviar mensaje"><Icon name="send" width={19}/></button>
        </div>
        {error ? <p className="message-error">{error}</p> : null}
      </form>
    </> : null}
  </section>;
}
