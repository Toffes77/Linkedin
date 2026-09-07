import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import type { MessageContact } from "./api.ts";
import {
  activeMessagingContacts,
  applyConnectionChanged,
} from "./connection-events.ts";

function contact({
  usuarioId,
  conversationId,
  connected,
}: {
  usuarioId: number;
  conversationId: number | null;
  connected: boolean;
}): MessageContact {
  return {
    usuario_id: usuarioId,
    nombre: `Usuario ${usuarioId}`,
    headline: "Perfil profesional",
    foto_perfil_url: null,
    conversacion_id: conversationId,
    ultimo_mensaje: null,
    ultimo_mensaje_autor_id: null,
    fecha_ultimo_mensaje: null,
    no_leidos: 0,
    conectados: connected,
  };
}

test("disconnect keeps historical conversations but removes inactive contacts without history", () => {
  const result = applyConnectionChanged(
    [
      contact({ usuarioId: 2, conversationId: 20, connected: true }),
      contact({ usuarioId: 3, conversationId: null, connected: true }),
    ],
    { usuarioId: 2, conectados: false },
  );

  assert.equal(result.length, 2);
  assert.equal(result[0].conversacion_id, 20);
  assert.equal(result[0].conectados, false);
  assert.deepEqual(
    applyConnectionChanged(result, { usuarioId: 3, conectados: false })
      .map((item) => item.usuario_id),
    [2],
  );
});

test("reconnection restores the same historical contact and conversation", () => {
  const historical = contact({
    usuarioId: 2,
    conversationId: 20,
    connected: false,
  });

  const [reconnected] = applyConnectionChanged(
    [historical],
    { usuarioId: 2, conectados: true },
  );

  assert.equal(reconnected.conectados, true);
  assert.equal(reconnected.conversacion_id, 20);
});

test("sharing only offers active connections", () => {
  const active = contact({ usuarioId: 2, conversationId: 20, connected: true });
  const historical = contact({ usuarioId: 3, conversationId: 30, connected: false });

  assert.deepEqual(
    activeMessagingContacts([active, historical]).map((item) => item.usuario_id),
    [2],
  );
});

test("profile requires two inline clicks before disconnecting", () => {
  const profile = readFileSync(
    new URL("../app/perfil/[id]/page.tsx", import.meta.url),
    "utf8",
  );

  assert.match(profile, /if \(!disconnectConfirming\)/);
  assert.match(profile, /setDisconnectConfirming\(true\);\s*return;/);
  assert.match(profile, /await disconnect\(\)/);
  assert.match(profile, /connectionsApi\.remove\(profile\.id\)/);
  assert.doesNotMatch(profile, /DisconnectConnectionModal|role="dialog"|aria-modal|disconnect-modal-backdrop/);
  assert.doesNotMatch(profile, /(?:window\.)?(?:alert|confirm)\s*\(/);
});

test("inline confirmation exposes confirm, cancel, loading and local errors", () => {
  const profile = readFileSync(
    new URL("../app/perfil/[id]/page.tsx", import.meta.url),
    "utf8",
  );

  assert.match(profile, /disconnectConfirming\s*\?\s*"Confirmar"/);
  assert.match(profile, /"Desconectando\.\.\."/);
  assert.match(profile, /¿Seguro que querés eliminar esta conexión\?/);
  assert.match(profile, /Podrás seguir viendo los mensajes anteriores/);
  assert.match(profile, /className="disconnect-cancel"[^>]*onClick=\{cancelDisconnect\}/);
  assert.match(profile, /setDisconnectConfirming\(false\)/);
  assert.match(profile, /role="alert"/);
  assert.match(profile, /className="profile-connection-action"/);
});

test("historical chat shows the divider and removes every writing action", () => {
  const chat = readFileSync(
    new URL("../components/messages/chat-window.tsx", import.meta.url),
    "utf8",
  );
  const share = readFileSync(
    new URL("../components/feed/share-post-modal.tsx", import.meta.url),
    "utf8",
  );

  assert.match(chat, /Ya no están conectados/);
  assert.match(chat, /connected \? <form className="message-composer"/);
  assert.match(chat, /if \(!connected\) return/);
  assert.match(share, /activeMessagingContacts/);
});

test("dock reacts immediately and polling refreshes remote disconnects", () => {
  const dock = readFileSync(
    new URL("../components/messages/messages-dock.tsx", import.meta.url),
    "utf8",
  );

  assert.match(dock, /CONNECTION_CHANGED_EVENT/);
  assert.match(dock, /setInterval/);
  assert.match(dock, /refreshContacts\(\)/);
  assert.match(dock, /connected=\{selected\.conectados\}/);
  assert.match(dock, /if \(!selected\?\.conversacion_id \|\| !selected\.conectados\) return/);
});

test("API contracts expose connection state and authenticated disconnect", () => {
  const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");

  assert.match(api, /conectados: boolean/);
  assert.match(api, /remove: \(userId: number\)/);
  assert.match(api, /method: "DELETE"/);
});
