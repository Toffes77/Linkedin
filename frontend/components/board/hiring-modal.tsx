"use client";

import { useEffect, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { boardApi, type HiringCompany, type Promotion } from "@/lib/api";

export function HiringModal({ promotion, onClose, onSent }: { promotion: Promotion; onClose: () => void; onSent: (message: string) => void }) {
  const [companies, setCompanies] = useState<HiringCompany[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    boardApi.getHiringCompanies(promotion.id, controller.signal)
      .then((items) => { setCompanies(items); if (items.length === 1) setSelected(items[0].empresa_id); })
      .catch((caught) => { if ((caught as Error).name !== "AbortError") setError(caught instanceof Error ? caught.message : "No se pudieron cargar tus empresas."); })
      .finally(() => setLoading(false));
    function closeOnEscape(event: KeyboardEvent) { if (event.key === "Escape") onClose(); }
    document.addEventListener("keydown", closeOnEscape);
    return () => { controller.abort(); document.removeEventListener("keydown", closeOnEscape); };
  }, [onClose, promotion.id]);

  async function confirm() {
    if (!selected) return;
    setSending(true);
    setError("");
    try {
      const company = companies.find((item) => item.empresa_id === selected);
      await boardApi.createHiringRequest(promotion.id, selected);
      onSent(`La propuesta de ${company?.nombre ?? "la empresa"} fue enviada.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo enviar la propuesta.");
    } finally {
      setSending(false);
    }
  }

  return <div className="board-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="board-modal hiring-modal card" role="dialog" aria-modal="true" aria-labelledby="hiring-modal-title">
      <header><div><span className="board-kicker">Contratar a {promotion.usuario_nombre}</span><h2 id="hiring-modal-title">¿Con qué empresa querés contratar?</h2></div><button type="button" className="board-close" onClick={onClose} aria-label="Cerrar">×</button></header>
      <div className="hiring-company-list">
        {loading ? <div className="board-state">Cargando empresas...</div> : companies.length ? companies.map((company) => <label className={`hiring-company ${selected === company.empresa_id ? "selected" : ""}`} key={company.empresa_id}>
          <input type="radio" name="company" checked={selected === company.empresa_id} onChange={() => setSelected(company.empresa_id)} />
          <Avatar name={company.nombre} src={company.foto_perfil_url} size={44}/>
          <span><strong>{company.nombre}</strong><small>{company.rol === "OWNER" ? "Propietario" : "Recruiter"}</small></span>
        </label>) : <div className="board-state">No tenés empresas habilitadas para esta contratación. Solo pueden hacerlo OWNER o RECRUITER, y la persona no debe ser miembro actual.</div>}
      </div>
      {error && <p className="inline-error" role="alert">{error}</p>}
      <footer><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button type="button" className="primary-button" disabled={!selected || sending} onClick={confirm}>{sending ? "Enviando..." : "Confirmar"}</button></footer>
    </section>
  </div>;
}
