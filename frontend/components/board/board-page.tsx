"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/common/icons";
import { AppShell } from "@/components/layout/app-shell";
import { boardApi, type Promotion } from "@/lib/api";
import { HiringModal } from "./hiring-modal";
import { PromotionCard } from "./promotion-card";
import { PromotionForm } from "./promotion-form";

type View = "public" | "mine";

export function BoardPage({ initialView, highlightedPromotion }: { initialView: View; highlightedPromotion: number | null }) {
  const [view, setView] = useState<View>(initialView);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);
  const [hiring, setHiring] = useState<Promotion | null>(null);
  const [acceptingId, setAcceptingId] = useState<number | null>(null);
  const [revision, setRevision] = useState(0);
  const pageSize = 10;

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => window.clearTimeout(timeout);
  }, [query]);

  useEffect(() => {
    const controller = new AbortController();
    const request = view === "mine"
      ? boardApi.getMyPromotions(controller.signal).then((items) => ({ items, total: items.length }))
      : boardApi.listPromotions(debouncedQuery, page, pageSize, controller.signal);
    request.then((result) => { setPromotions(result.items); setTotal(result.total); })
      .catch((caught) => { if ((caught as Error).name !== "AbortError") setError(caught instanceof Error ? caught.message : "No se pudieron cargar las promociones."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [debouncedQuery, page, revision, view]);

  useEffect(() => {
    if (!highlightedPromotion || loading || view !== "mine") return;
    document.getElementById(`promocion-${highlightedPromotion}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlightedPromotion, loading, view]);

  const closeCreate = useCallback(() => setCreating(false), []);
  const closeHiring = useCallback(() => setHiring(null), []);

  function changeView(next: View) {
    setLoading(true);
    setView(next);
    setPage(1);
    setError("");
    setNotice("");
  }

  async function acceptRequest(requestId: number) {
    setAcceptingId(requestId);
    setError("");
    try {
      await boardApi.acceptHiringRequest(requestId);
      setNotice("Contratación aceptada. Ya formás parte de la empresa.");
      setLoading(true);
      setRevision((value) => value + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo aceptar la contratación.");
    } finally {
      setAcceptingId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return <AppShell><main className="app-background"><div className="board-layout">
    <section className="board-hero card">
      <div><span className="board-kicker">Oportunidades profesionales</span><h1>Tablón</h1><p>Mostrá tu trabajo o encontrá el perfil que tu empresa necesita.</p></div>
      <button type="button" className="primary-button" onClick={() => setCreating(true)}>Crear promoción</button>
    </section>
    <section className="board-toolbar card">
      <div className="board-tabs" role="tablist" aria-label="Vistas del Tablón"><button type="button" role="tab" aria-selected={view === "public"} className={view === "public" ? "active" : ""} onClick={() => changeView("public")}>Profesionales</button><button type="button" role="tab" aria-selected={view === "mine"} className={view === "mine" ? "active" : ""} onClick={() => changeView("mine")}>Mis promociones</button></div>
      {view === "public" && <label className="board-search"><Icon name="search" width={21}/><span className="sr-only">Buscar profesionales por título</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); setLoading(true); setError(""); }} placeholder="Buscar profesionales" /></label>}
    </section>
    {notice && <p className="notice notice-success" role="status">{notice}</p>}
    {error && <p className="notice notice-error" role="alert">{error}</p>}
    <section className="promotion-list" aria-live="polite">
      {loading ? Array.from({ length: 3 }, (_, index) => <div className="promotion-skeleton card skeleton" key={index}/>) : promotions.length ? promotions.map((promotion) => <PromotionCard key={promotion.id} promotion={promotion} own={view === "mine"} highlighted={highlightedPromotion === promotion.id} acceptingId={acceptingId} onHire={setHiring} onAccept={acceptRequest}/>) : <div className="board-empty card">{view === "mine" ? "Todavía no creaste ninguna promoción." : "No se encontraron promociones."}</div>}
    </section>
    {view === "public" && !loading && totalPages > 1 && <nav className="board-pagination" aria-label="Paginación del Tablón"><button type="button" className="secondary-button" disabled={page === 1} onClick={() => { setLoading(true); setPage((value) => value - 1); }}>Anterior</button><span>Página {page} de {totalPages}</span><button type="button" className="secondary-button" disabled={page === totalPages} onClick={() => { setLoading(true); setPage((value) => value + 1); }}>Siguiente</button></nav>}
  </div></main>
  {creating && <PromotionForm onClose={closeCreate} onCreated={() => { setCreating(false); changeView("mine"); setNotice("Tu promoción fue publicada."); setRevision((value) => value + 1); }}/>} 
  {hiring && <HiringModal promotion={hiring} onClose={closeHiring} onSent={(message) => { setHiring(null); setNotice(message); setLoading(true); setRevision((value) => value + 1); }}/>} 
  </AppShell>;
}
