"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef } from "react";
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

  return <section className={`message-chat-window${minimized ? " minimized" : ""}`} aria-label={`Conversación con ${contact.nombre}`}>
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
      <div className="message-history" ref={historyRef}>
        {canLoadPrevious ? <button type="button" className="message-load-previous" onClick={onLoadPrevious}>Cargar mensajes anteriores</button> : null}
        {messages.length === 0 ? <div className="message-empty-chat"><Avatar name={contact.nombre} src={contact.foto_perfil_url} size={64}/><strong>{contact.nombre}</strong><span>Este es el comienzo de la conversación.</span></div> : null}
        {messages.map((message) => <div className={`message-bubble-row${message.autor_id === currentUserId ? " own" : ""}`} key={message.id}>
          {message.autor_id !== currentUserId ? <Avatar name={contact.nombre} src={contact.foto_perfil_url} size={30}/> : null}
          <div className="message-bubble"><p>{message.contenido}</p><time>{messageTime(message.fecha)}</time></div>
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

