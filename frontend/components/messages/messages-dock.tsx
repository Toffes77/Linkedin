"use client";

import { CSSProperties, PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FaEdit, FaSlidersH } from "react-icons/fa";
import { MdKeyboardArrowUp } from "react-icons/md";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";
import { ChatWindow } from "@/components/messages/chat-window";
import { ConversationList } from "@/components/messages/conversation-list";
import { MessagePreferencesMenu } from "@/components/messages/message-preferences";
import {
  DEFAULT_MESSAGE_PREFERENCES,
  deleteMessageBackgroundImage,
  loadMessageBackgroundImage,
  MESSAGE_PREFERENCES_STORAGE_KEY,
  messageFontFamily,
  parseMessagePreferences,
  saveMessageBackgroundImage,
  type MessageFontId,
  type MessagePreferences,
} from "@/components/messages/message-preferences-storage";
import { MessageResizeHandles, type MessageResizeDirection } from "@/components/messages/message-resize-handles";
import { ApiError, messagesApi, type MessageContact, type PrivateMessage } from "@/lib/api";

const PAGE_SIZE = 50;
const POLLING_MS = 5000;
const DESKTOP_MEDIA_QUERY = "(min-width: 851px)";
const MIN_PANEL_WIDTH = 320;
const MIN_PANEL_HEIGHT = 360;
const MAX_PANEL_WIDTH = 720;
const MAX_PANEL_HEIGHT = 720;

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
  const [preferences, setPreferences] = useState<MessagePreferences>(() => {
    if (typeof window === "undefined") return DEFAULT_MESSAGE_PREFERENCES;
    try {
      return parseMessagePreferences(window.localStorage.getItem(MESSAGE_PREFERENCES_STORAGE_KEY));
    } catch {
      return DEFAULT_MESSAGE_PREFERENCES;
    }
  });
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [backgroundImageUrl, setBackgroundImageUrl] = useState<string | null>(null);
  const [resizeMode, setResizeMode] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [viewport, setViewport] = useState({ width: 0, height: 0 });
  const selectedRef = useRef<MessageContact | null>(null);
  const chatVisibleRef = useRef(false);
  const panelRef = useRef<HTMLElement>(null);
  const preferencesMenuRef = useRef<HTMLDivElement>(null);
  const preferencesButtonRef = useRef<HTMLButtonElement>(null);
  const backgroundImageUrlRef = useRef<string | null>(null);
  const resizeCleanupRef = useRef<() => void>(() => undefined);

  useEffect(() => { selectedRef.current = selected; }, [selected]);
  useEffect(() => { chatVisibleRef.current = Boolean(selected && !chatMinimized); }, [selected, chatMinimized]);

  const replaceBackgroundImageUrl = useCallback((next: string | null) => {
    if (backgroundImageUrlRef.current) URL.revokeObjectURL(backgroundImageUrlRef.current);
    backgroundImageUrlRef.current = next;
    setBackgroundImageUrl(next);
  }, []);

  useEffect(() => {
    let active = true;
    void loadMessageBackgroundImage().then((image) => {
      if (active && image) replaceBackgroundImageUrl(URL.createObjectURL(image));
    }).catch(() => {
      // IndexedDB puede estar deshabilitado; el resto de preferencias sigue disponible.
    });
    return () => {
      active = false;
      if (backgroundImageUrlRef.current) URL.revokeObjectURL(backgroundImageUrlRef.current);
    };
  }, [replaceBackgroundImageUrl]);

  useEffect(() => {
    try {
      window.localStorage.setItem(MESSAGE_PREFERENCES_STORAGE_KEY, JSON.stringify(preferences));
    } catch {
      // El panel sigue funcionando si el navegador bloquea localStorage.
    }
  }, [preferences]);

  useEffect(() => () => resizeCleanupRef.current(), []);

  useEffect(() => {
    const media = window.matchMedia(DESKTOP_MEDIA_QUERY);
    const updateViewport = () => {
      const desktop = media.matches;
      setIsDesktop(desktop);
      setViewport({ width: document.documentElement.clientWidth, height: window.innerHeight });
      if (!desktop) setResizeMode(false);
    };
    updateViewport();
    media.addEventListener("change", updateViewport);
    window.addEventListener("resize", updateViewport);
    return () => {
      media.removeEventListener("change", updateViewport);
      window.removeEventListener("resize", updateViewport);
    };
  }, []);

  useEffect(() => {
    function keyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") return;
      resizeCleanupRef.current();
      setPreferencesOpen(false);
      setResizeMode(false);
    }
    function pointerDown(event: globalThis.PointerEvent) {
      if (!preferencesOpen) return;
      const target = event.target as Node;
      if (!preferencesMenuRef.current?.contains(target) && !preferencesButtonRef.current?.contains(target)) {
        setPreferencesOpen(false);
      }
    }
    window.addEventListener("keydown", keyDown);
    window.addEventListener("pointerdown", pointerDown);
    return () => {
      window.removeEventListener("keydown", keyDown);
      window.removeEventListener("pointerdown", pointerDown);
    };
  }, [preferencesOpen]);

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
  const panelLimits = useMemo(() => {
    const horizontalMargin = 44;
    const adjacentChatWidth = selected ? (chatMinimized ? 315 : 400) + 14 : 0;
    const availableWidth = Math.max(MIN_PANEL_WIDTH, viewport.width - horizontalMargin - adjacentChatWidth);
    const availableHeight = Math.max(240, viewport.height - 86);
    return {
      minWidth: Math.min(MIN_PANEL_WIDTH, availableWidth),
      minHeight: Math.min(MIN_PANEL_HEIGHT, availableHeight),
      maxWidth: Math.min(MAX_PANEL_WIDTH, availableWidth),
      maxHeight: Math.min(MAX_PANEL_HEIGHT, availableHeight),
    };
  }, [chatMinimized, selected, viewport]);
  const displayedPanelWidth = Math.min(Math.max(preferences.panelWidth, panelLimits.minWidth), panelLimits.maxWidth);
  const displayedPanelHeight = Math.min(Math.max(preferences.panelHeight, panelLimits.minHeight), panelLimits.maxHeight);
  const panelStyle: CSSProperties | undefined = isDesktop ? {
    width: displayedPanelWidth,
    ...(expanded ? { height: displayedPanelHeight } : {}),
  } : undefined;

  function startResize(direction: MessageResizeDirection, event: ReactPointerEvent<HTMLButtonElement>) {
    if (!isDesktop || !expanded || !panelRef.current) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeCleanupRef.current();
    const startX = event.clientX;
    const startY = event.clientY;
    const startBounds = panelRef.current.getBoundingClientRect();

    function pointerMove(moveEvent: globalThis.PointerEvent) {
      moveEvent.preventDefault();
      const changesWidth = direction === "width" || direction === "both";
      const changesHeight = direction === "height" || direction === "both";
      const width = changesWidth ? startBounds.width + startX - moveEvent.clientX : startBounds.width;
      const height = changesHeight ? startBounds.height + startY - moveEvent.clientY : startBounds.height;
      setPreferences((current) => ({
        ...current,
        panelWidth: Math.round(Math.min(Math.max(width, panelLimits.minWidth), panelLimits.maxWidth)),
        panelHeight: Math.round(Math.min(Math.max(height, panelLimits.minHeight), panelLimits.maxHeight)),
      }));
    }

    function removeResizeListeners() {
      window.removeEventListener("pointermove", pointerMove);
      window.removeEventListener("pointerup", removeResizeListeners);
      window.removeEventListener("pointercancel", removeResizeListeners);
    }

    window.addEventListener("pointermove", pointerMove);
    window.addEventListener("pointerup", removeResizeListeners);
    window.addEventListener("pointercancel", removeResizeListeners);
    resizeCleanupRef.current = removeResizeListeners;
  }

  async function clearBackgroundImage() {
    try {
      await deleteMessageBackgroundImage();
    } catch {
      // La preferencia visible se restablece aunque el navegador bloquee IndexedDB.
    }
    replaceBackgroundImageUrl(null);
  }

  async function selectBackgroundColor(backgroundColor: string) {
    await clearBackgroundImage();
    setPreferences((current) => ({ ...current, backgroundColor }));
  }

  async function selectBackgroundImage(image: File) {
    await saveMessageBackgroundImage(image);
    replaceBackgroundImageUrl(URL.createObjectURL(image));
  }

  async function resetBackground() {
    await clearBackgroundImage();
    setPreferences((current) => ({ ...current, backgroundColor: DEFAULT_MESSAGE_PREFERENCES.backgroundColor }));
  }

  async function resetPreferences() {
    await clearBackgroundImage();
    setPreferences({ ...DEFAULT_MESSAGE_PREFERENCES });
    setResizeMode(false);
  }

  function togglePanel() {
    if (expanded) {
      setPreferencesOpen(false);
      setResizeMode(false);
    }
    setExpanded((value) => !value);
  }

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
      backgroundColor={preferences.backgroundColor}
      backgroundImageUrl={backgroundImageUrl}
      messageFontFamily={messageFontFamily(preferences.font)}
    /> : null}
    <section
      ref={panelRef}
      className={`messages-panel${expanded ? " expanded" : ""}${resizeMode ? " resize-mode" : ""}`}
      style={panelStyle}
      aria-label="Mensajes privados"
    >
      <header className="messages-panel-header">
        <button className="messages-panel-toggle" type="button" onClick={togglePanel} aria-expanded={expanded}>
          <span className="messages-self-avatar"><Avatar name={userName} src={user?.foto_perfil_url} size={42}/>{unread ? <span className="messages-general-dot"/> : null}</span>
          <strong>Mensajes</strong>
          {unread ? <span className="sr-only">Hay mensajes sin leer</span> : null}
        </button>
        <div className="message-header-actions">
          <button
            type="button"
            className={resizeMode ? "active" : ""}
            disabled={!isDesktop}
            onClick={() => { setExpanded(true); setPreferencesOpen(false); setResizeMode((value) => !value); }}
            aria-label="Cambiar tamaño de Mensajes"
            aria-pressed={resizeMode}
            title={isDesktop ? "Cambiar tamaño de Mensajes" : "El cambio de tamaño está disponible en pantallas grandes"}
          ><FaEdit aria-hidden="true"/></button>
          <button
            ref={preferencesButtonRef}
            type="button"
            className={preferencesOpen ? "active" : ""}
            onClick={() => { setExpanded(true); setResizeMode(false); setPreferencesOpen((value) => !value); }}
            aria-label="Preferencias de Mensajes"
            aria-expanded={preferencesOpen}
            title="Preferencias de Mensajes"
          ><FaSlidersH aria-hidden="true"/></button>
          <button
            type="button"
            onClick={togglePanel}
            aria-label={expanded ? "Minimizar Mensajes" : "Abrir Mensajes"}
            title={expanded ? "Minimizar Mensajes" : "Abrir Mensajes"}
          ><MdKeyboardArrowUp className={`messages-panel-arrow${expanded ? " expanded" : ""}`} aria-hidden="true"/></button>
        </div>
      </header>
      {preferencesOpen ? <MessagePreferencesMenu
        menuRef={preferencesMenuRef}
        preferences={preferences}
        hasCustomImage={Boolean(backgroundImageUrl)}
        onBackgroundColorChange={selectBackgroundColor}
        onImageSelected={selectBackgroundImage}
        onResetBackground={resetBackground}
        onFontChange={(font: MessageFontId) => setPreferences((current) => ({ ...current, font }))}
        onResetPreferences={resetPreferences}
      /> : null}
      {expanded ? <ConversationList
        contacts={contacts}
        query={query}
        onQueryChange={setQuery}
        onSelect={selectContact}
        loading={loadingContacts}
        selectedUserId={selected?.usuario_id ?? null}
      /> : null}
      {expanded && chatError && !selected ? <p className="messages-panel-error">{chatError}</p> : null}
      {expanded && resizeMode && isDesktop ? <>
        <span className="message-resize-hint" role="status">Arrastrá los bordes para cambiar el tamaño</span>
        <MessageResizeHandles onResizeStart={startResize}/>
      </> : null}
    </section>
  </div>;
}
