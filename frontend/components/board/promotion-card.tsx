"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import type { Promotion } from "@/lib/api";
import { formatRelativeDate } from "@/lib/format";

type Action = "accept" | "reject";

export function PromotionCard({ promotion, own = false, highlighted = false, respondingId, onHire, onRespond }: { promotion: Promotion; own?: boolean; highlighted?: boolean; respondingId?: number | null; onHire?: (promotion: Promotion) => void; onRespond?: (requestId: number, action: Action) => void }) {
  const [confirmation, setConfirmation] = useState<{ id: number; action: Action } | null>(null);
  useEffect(() => {
    if (!confirmation) return;
    const timeout = window.setTimeout(() => setConfirmation(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [confirmation]);

  function respond(requestId: number, action: Action) {
    if (confirmation?.id !== requestId || confirmation.action !== action) {
      setConfirmation({ id: requestId, action });
      return;
    }
    setConfirmation(null);
    onRespond?.(requestId, action);
  }

  const statusLabel = promotion.estado === "CONTRATADO" ? "Contratado" : promotion.estado === "PENDIENTE_CONTRATACION" ? "Pendiente contratación" : "Pendiente";
  return <article id={`promocion-${promotion.id}`} className={`promotion-card card ${highlighted ? "highlighted" : ""}`}>
    <header>
      <Link href={`/perfil/${promotion.usuario_id}`} className="promotion-author"><Avatar name={promotion.usuario_nombre} src={promotion.usuario_foto_perfil_url} size={54}/><span><strong>{promotion.usuario_nombre}</strong>{promotion.usuario_headline && <small>{promotion.usuario_headline}</small>}<time dateTime={promotion.fecha_creacion}>{formatRelativeDate(promotion.fecha_creacion)}</time></span></Link>
      {own && <span className={`promotion-status ${promotion.estado !== "PENDIENTE" ? "active" : ""}`}>{statusLabel}</span>}
    </header>
    <div className="promotion-content"><h2>{promotion.titulo}</h2><p>{promotion.descripcion}</p></div>
    {own ? <div className="promotion-requests">
      {promotion.estado === "CONTRATADO" && promotion.solicitud_aceptada && <div className="promotion-request promotion-request-complete"><Avatar name={promotion.solicitud_aceptada.empresa_nombre} src={promotion.solicitud_aceptada.empresa_foto_perfil_url} size={42}/><span><strong>Contratado por {promotion.solicitud_aceptada.empresa_nombre}</strong><small>Esta promoción quedó cerrada.</small></span></div>}
      {promotion.solicitudes_pendientes.map((request) => {
        const confirming = confirmation?.id === request.id ? confirmation.action : null;
        const busy = respondingId === request.id;
        return <div className="promotion-request" key={request.id}>
          <Avatar name={request.empresa_nombre} src={request.empresa_foto_perfil_url} size={42}/>
          <span><strong>{request.empresa_nombre} quiere contratarte</strong><small>Propuesta recibida desde tu promoción</small></span>
          <div className="promotion-request-actions">
            <button type="button" className={confirming === "accept" ? "confirm-button" : "primary-button"} disabled={busy} onClick={() => respond(request.id, "accept")}>{busy && confirming === "accept" ? "Aceptando..." : confirming === "accept" ? "¿Confirmar aceptación?" : "Aceptar"}</button>
            <button type="button" className={confirming === "reject" ? "confirm-button" : "secondary-button"} disabled={busy} onClick={() => respond(request.id, "reject")}>{busy && confirming === "reject" ? "Rechazando..." : confirming === "reject" ? "¿Confirmar rechazo?" : "Rechazar"}</button>
          </div>
        </div>;
      })}
    </div> : <footer><button type="button" className="primary-button" onClick={() => onHire?.(promotion)}>Contratar</button></footer>}
  </article>;
}
