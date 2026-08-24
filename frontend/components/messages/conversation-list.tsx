"use client";

import { useMemo } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import type { MessageContact } from "@/lib/api";

function normalizeName(value: string) {
  return value.trim().toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function relativeDate(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  const diff = Math.max(0, Date.now() - date.getTime());
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "ayer" : `${days} d`;
}

export function ConversationList({
  contacts,
  query,
  onQueryChange,
  onSelect,
  loading,
  selectedUserId,
}: {
  contacts: MessageContact[];
  query: string;
  onQueryChange: (value: string) => void;
  onSelect: (contact: MessageContact) => void;
  loading: boolean;
  selectedUserId: number | null;
}) {
  const filtered = useMemo(() => {
    const normalized = normalizeName(query);
    if (!normalized) return contacts;
    return contacts.filter((contact) => normalizeName(contact.nombre).includes(normalized));
  }, [contacts, query]);

  return <>
    <label className="messages-search">
      <Icon name="search" width={22}/>
      <span className="sr-only">Buscar contactos por nombre</span>
      <input
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="Buscar mensajes"
        autoComplete="off"
      />
      <span className="messages-filter-mark" aria-hidden="true">☷</span>
    </label>
    <div className="messages-list" key={normalizeName(query)}>
      {loading && contacts.length === 0 ? <p className="messages-list-state">Cargando contactos...</p> : null}
      {!loading && filtered.length === 0 ? <p className="messages-list-state">No se encontraron contactos</p> : null}
      {filtered.map((contact) => <button
        type="button"
        className={`message-contact-row${selectedUserId === contact.usuario_id ? " selected" : ""}`}
        key={contact.usuario_id}
        onClick={() => onSelect(contact)}
      >
        <Avatar name={contact.nombre} src={contact.foto_perfil_url} size={48}/>
        <span className="message-contact-copy">
          <span className="message-contact-heading">
            <strong>{contact.nombre}</strong>
            <small>{relativeDate(contact.fecha_ultimo_mensaje)}</small>
          </span>
          <span className="message-contact-preview">
            {contact.ultimo_mensaje
              ? `${contact.ultimo_mensaje_autor_id === contact.usuario_id ? "" : "Vos: "}${contact.ultimo_mensaje}`
              : contact.headline || "Iniciá una conversación"}
          </span>
        </span>
        {contact.no_leidos > 0 ? <span className="message-unread-dot" aria-label={`${contact.no_leidos} mensajes sin leer`}/> : null}
      </button>)}
    </div>
  </>;
}

