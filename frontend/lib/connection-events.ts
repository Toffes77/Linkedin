import type { MessageContact } from "./api";

export const CONNECTION_CHANGED_EVENT = "atanes:connection-changed";

export type ConnectionChangedDetail = {
  usuarioId: number;
  conectados: boolean;
};

export function emitConnectionChanged(detail: ConnectionChangedDetail) {
  window.dispatchEvent(
    new CustomEvent<ConnectionChangedDetail>(CONNECTION_CHANGED_EVENT, {
      detail,
    }),
  );
}

export function applyConnectionChanged(
  contacts: MessageContact[],
  detail: ConnectionChangedDetail,
) {
  return contacts
    .map((contact) => contact.usuario_id === detail.usuarioId
      ? { ...contact, conectados: detail.conectados }
      : contact)
    .filter((contact) => contact.conectados || contact.conversacion_id !== null);
}

export function activeMessagingContacts(contacts: MessageContact[]) {
  return contacts.filter((contact) => contact.conectados);
}
