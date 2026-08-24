"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { ChatWindow } from "@/components/messages/chat-window";
import { ConversationList } from "@/components/messages/conversation-list";
import { ApiError, messagesApi, type MessageContact, type PrivateMessage } from "@/lib/api";

const PAGE_SIZE = 50;
const POLLING_MS = 5000;

function mergeMessages(current: PrivateMessage[], incoming: PrivateMessage[]) {
  const byId = new Map(current.map((message) => [message.id, message]));
  incoming.forEach((message) => byId.set(message.id, message));
  return [...byId.values()].sort((a, b) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime() || a.id - b.id);
}

export function MessagesDock() {
  const { user } = useAuth();
  const userId = user?.id ?? 0;
  const userName = user?.nombre ?? "Usuario";
  const [expanded, setExpanded] = useState(false);
  const [contacts, setContacts] = useState<MessageContact[]>([]);
  const [query, setQuery] = useState("");
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [selected, setSelected] = useState<MessageContact | null>(null);
  const [chatMinimized, setChatMinimized] = useState(false);
  const [messagesByConversation, setMessagesByConversation] = useState<Record<number, PrivateMessage[]>>({});
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [canLoadPrevious, setCanLoadPrevious] = useState<Record<number, boolean>>({});
  const selectedRef = useRef<MessageContact | null>(null);
  const chatVisibleRef = useRef(false);

  useEffect(() => { selectedRef.current = selected; }, [selected]);
  useEffect(() => { chatVisibleRef.current = Boolean(selected && !chatMinimized); }, [selected, chatMinimized]);

  const refreshContacts = useCallback(async () => {
    try {
      const next = await messagesApi.listConversations();
      const active = selectedRef.current;
      if (active && chatVisibleRef.current && active.conversacion_id) {
        const activeIndex = next.findIndex((item) => item.usuario_id === active.usuario_id);
        if (activeIndex >= 0 && next[activeIndex].no_leidos > 0) {
          await messagesApi.markAsRead(active.conversacion_id);
          next[activeIndex] = { ...next[activeIndex], no_leidos: 0 };
        }
      }
      setContacts(next);
      if (active) {
        const updated = next.find((item) => item.usuario_id === active.usuario_id);
        if (updated) setSelected(updated);
      }
    } catch {
      // El dock no interrumpe la navegación si una actualización periódica falla.
    } finally {
      setLoadingContacts(false);
    }
  }, []);

  const refreshActiveMessages = useCallback(async () => {
    const active = selectedRef.current;
    if (!active?.conversacion_id) return;
    try {
      const latest = await messagesApi.getMessages(active.conversacion_id, PAGE_SIZE, 0);
      setMessagesByConversation((current) => ({
        ...current,
        [active.conversacion_id!]: mergeMessages(current[active.conversacion_id!] ?? [], latest),
      }));
      if (chatVisibleRef.current && latest.some((message) => message.autor_id !== userId)) {
        await messagesApi.markAsRead(active.conversacion_id);
        setContacts((current) => current.map((item) => item.usuario_id === active.usuario_id ? { ...item, no_leidos: 0 } : item));
      }
    } catch {
      // Se conserva el historial ya cargado y se reintenta en el próximo ciclo.
    }
  }, [userId]);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refreshContacts(), 0);
    const interval = window.setInterval(() => {
      void refreshContacts();
      void refreshActiveMessages();
    }, POLLING_MS);
    return () => {
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
    };
  }, [refreshActiveMessages, refreshContacts]);

  async function selectContact(contact: MessageContact) {
    setChatError(null);
    try {
      let conversationId = contact.conversacion_id;
      if (!conversationId) {
        const conversation = await messagesApi.getOrCreateConversation(contact.usuario_id);
        conversationId = conversation.id;
      }
      const active = { ...contact, conversacion_id: conversationId, no_leidos: 0 };
      setSelected(active);
      setChatMinimized(false);
      selectedRef.current = active;
      chatVisibleRef.current = true;
      if (!messagesByConversation[conversationId]) {
        const messages = await messagesApi.getMessages(conversationId, PAGE_SIZE, 0);
        setMessagesByConversation((current) => ({ ...current, [conversationId!]: messages }));
        setCanLoadPrevious((current) => ({ ...current, [conversationId!]: messages.length === PAGE_SIZE }));
      }
      await messagesApi.markAsRead(conversationId);
      setContacts((current) => current.map((item) => item.usuario_id === contact.usuario_id ? { ...item, conversacion_id: conversationId, no_leidos: 0 } : item));
    } catch (error) {
      setChatError(error instanceof ApiError ? error.message : "No se pudo abrir la conversación.");
    }
  }

  async function sendMessage() {
    if (!selected?.conversacion_id) return;
    const draft = drafts[selected.usuario_id] ?? "";
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    setChatError(null);
    try {
      const message = await messagesApi.sendMessage(selected.conversacion_id, content);
      setMessagesByConversation((current) => ({
        ...current,
        [selected.conversacion_id!]: mergeMessages(current[selected.conversacion_id!] ?? [], [message]),
      }));
      setDrafts((current) => ({ ...current, [selected.usuario_id]: "" }));
      await refreshContacts();
    } catch (error) {
      setChatError(error instanceof ApiError ? error.message : "No se pudo enviar el mensaje.");
    } finally {
      setSending(false);
    }
  }

  async function loadPrevious() {
    if (!selected?.conversacion_id) return;
    const current = messagesByConversation[selected.conversacion_id] ?? [];
    try {
      const previous = await messagesApi.getMessages(selected.conversacion_id, PAGE_SIZE, current.length);
      setMessagesByConversation((all) => ({ ...all, [selected.conversacion_id!]: mergeMessages(previous, all[selected.conversacion_id!] ?? []) }));
      setCanLoadPrevious((all) => ({ ...all, [selected.conversacion_id!]: previous.length === PAGE_SIZE }));
    } catch (error) {
      setChatError(error instanceof ApiError ? error.message : "No se pudieron cargar mensajes anteriores.");
    }
  }

  const unread = useMemo(() => contacts.some((contact) => contact.no_leidos > 0), [contacts]);
  const selectedMessages = selected?.conversacion_id ? messagesByConversation[selected.conversacion_id] ?? [] : [];

  return <div className="messages-dock-layer">
    {selected ? <ChatWindow
      contact={selected}
      currentUserId={userId}
      messages={selectedMessages}
      draft={drafts[selected.usuario_id] ?? ""}
      minimized={chatMinimized}
      busy={sending}
      error={chatError}
      canLoadPrevious={selected.conversacion_id ? Boolean(canLoadPrevious[selected.conversacion_id]) : false}
      onDraftChange={(value) => setDrafts((current) => ({ ...current, [selected.usuario_id]: value }))}
      onSend={sendMessage}
      onLoadPrevious={loadPrevious}
      onMinimize={() => setChatMinimized((value) => !value)}
      onClose={() => { setSelected(null); setChatError(null); }}
    /> : null}
    <section className={`messages-panel${expanded ? " expanded" : ""}`} aria-label="Mensajes privados">
      <header className="messages-panel-header">
        <button className="messages-panel-toggle" type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
          <span className="messages-self-avatar"><Avatar name={userName} src={user?.foto_perfil_url} size={42}/>{unread ? <span className="messages-general-dot"/> : null}</span>
          <strong>Mensajes</strong>
          {unread ? <span className="sr-only">Hay mensajes sin leer</span> : null}
        </button>
        <div className="message-header-actions">
          <button type="button" aria-label="Más opciones"><Icon name="more" width={22}/></button>
          <button type="button" onClick={() => { setExpanded(true); setQuery(""); }} aria-label="Nuevo mensaje"><Icon name="edit" width={20}/></button>
          <button type="button" onClick={() => setExpanded((value) => !value)} aria-label={expanded ? "Minimizar mensajes" : "Abrir mensajes"}>{expanded ? "⌄" : "⌃"}</button>
        </div>
      </header>
      {expanded ? <ConversationList
        contacts={contacts}
        query={query}
        onQueryChange={setQuery}
        onSelect={selectContact}
        loading={loadingContacts}
        selectedUserId={selected?.usuario_id ?? null}
      /> : null}
      {expanded && chatError && !selected ? <p className="messages-panel-error">{chatError}</p> : null}
    </section>
  </div>;
}
