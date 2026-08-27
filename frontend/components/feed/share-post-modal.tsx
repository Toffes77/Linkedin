"use client";

import { useEffect, useMemo, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { ApiError, messagesApi, type MessageContact, type Post } from "@/lib/api";

function normalize(value: string) {
  return value.trim().toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

export function SharePostModal({
  post,
  onClose,
  onSent,
}: {
  post: Post;
  onClose: () => void;
  onSent: (contactName: string) => void;
}) {
  const [contacts, setContacts] = useState<MessageContact[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [sendingTo, setSendingTo] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    messagesApi.listConversations()
      .then((items) => {
        if (active) setContacts(items);
      })
      .catch((reason) => {
        if (active) setError(reason instanceof ApiError ? reason.message : "No se pudieron cargar tus contactos.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && sendingTo === null) onClose();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose, sendingTo]);

  const filtered = useMemo(() => {
    const term = normalize(query);
    if (!term) return contacts;
    return contacts.filter((contact) => normalize(contact.nombre).includes(term));
  }, [contacts, query]);

  async function share(contact: MessageContact) {
    if (sendingTo !== null) return;
    setSendingTo(contact.usuario_id);
    setError("");
    try {
      const conversationId = contact.conversacion_id
        ?? (await messagesApi.getOrCreateConversation(contact.usuario_id)).id;
      await messagesApi.sharePost(conversationId, post.id);
      onSent(contact.nombre);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "No se pudo enviar la publicación.");
      setSendingTo(null);
    }
  }

  return <div className="share-post-overlay" role="presentation" onMouseDown={(event) => {
    if (event.target === event.currentTarget && sendingTo === null) onClose();
  }}>
    <section className="share-post-modal" role="dialog" aria-modal="true" aria-labelledby={`share-post-title-${post.id}`}>
      <header>
        <h2 id={`share-post-title-${post.id}`}>Enviar publicación</h2>
        <button type="button" onClick={onClose} disabled={sendingTo !== null} aria-label="Cerrar"><span aria-hidden="true">×</span></button>
      </header>
      <label className="share-contact-search">
        <Icon name="search" width={20}/>
        <span className="sr-only">Buscar contacto</span>
        <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar contacto..." autoComplete="off"/>
      </label>
      {error ? <p className="inline-error share-post-error" role="alert">{error}</p> : null}
      <div className="share-contact-list">
        {loading ? <p className="share-post-state">Cargando contactos...</p> : null}
        {!loading && filtered.length === 0 ? <p className="share-post-state">No se encontraron contactos.</p> : null}
        {filtered.map((contact) => <button type="button" key={contact.usuario_id} disabled={sendingTo !== null} onClick={() => void share(contact)}>
          <Avatar name={contact.nombre} src={contact.foto_perfil_url} size={44}/>
          <span><strong>{contact.nombre}</strong><small>{contact.headline}</small></span>
          {sendingTo === contact.usuario_id ? <span className="session-spinner" aria-label="Enviando"/> : <Icon name="send" width={19}/>} 
        </button>)}
      </div>
    </section>
  </div>;
}
