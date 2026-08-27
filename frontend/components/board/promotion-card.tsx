"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import type { Promotion } from "@/lib/api";
import { formatRelativeDate } from "@/lib/format";

export function PromotionCard({ promotion, own = false, highlighted = false, acceptingId, onHire, onAccept }: { promotion: Promotion; own?: boolean; highlighted?: boolean; acceptingId?: number | null; onHire?: (promotion: Promotion) => void; onAccept?: (requestId: number) => void }) {
  const [confirmationId, setConfirmationId] = useState<number | null>(null);
  useEffect(() => {
    if (!confirmationId) return;
    const timeout = window.setTimeout(() => setConfirmationId(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [confirmationId]);

  function accept(requestId: number) {
    if (confirmationId !== requestId) { setConfirmationId(requestId); return; }
    setConfirmationId(null);
    onAccept?.(requestId);
  }

  return <article id={`promocion-${promotion.id}`} className={`promotion-card card ${highlighted ? "highlighted" : ""}`}>
    <header>
      <Link href={`/perfil/${promotion.usuario_id}`} className="promotion-author"><Avatar name={promotion.usuario_nombre} src={promotion.usuario_foto_perfil_url} size={54}/><span><strong>{promotion.usuario_nombre}</strong>{promotion.usuario_headline && <small>{promotion.usuario_headline}</small>}<time dateTime={promotion.fecha_creacion}>{formatRelativeDate(promotion.fecha_creacion)}</time></span></Link>
      {own && <span className={`promotion-status ${promotion.estado === "PENDIENTE_CONTRATACION" ? "active" : ""}`}>{promotion.estado === "PENDIENTE_CONTRATACION" ? "Pendiente contratación" : "Pendiente"}</span>}
    </header>
    <div className="promotion-content"><h2>{promotion.titulo}</h2><p>{promotion.descripcion}</p></div>
    {own ? <div className="promotion-requests">
      {promotion.solicitudes_pendientes.map((request) => <div className="promotion-request" key={request.id}>
        <Avatar name={request.empresa_nombre} src={request.empresa_foto_perfil_url} size={42}/>
        <span><strong>{request.empresa_nombre} quiere contratarte</strong><small>Propuesta recibida desde tu promoción</small></span>
        <button type="button" className={confirmationId === request.id ? "confirm-button" : "primary-button"} disabled={acceptingId === request.id} onClick={() => accept(request.id)}>{acceptingId === request.id ? "Aceptando..." : confirmationId === request.id ? "¿Confirmar?" : "Aceptar contratación"}</button>
      </div>)}
    </div> : <footer><button type="button" className="primary-button" onClick={() => onHire?.(promotion)}>Contratar</button></footer>}
  </article>;
}
