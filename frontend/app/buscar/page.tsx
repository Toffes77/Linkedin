"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { PersonCard } from "@/components/network/person-card";
import { usersApi, type User } from "@/lib/api";

function SearchResults() {
  const params = useSearchParams();
  const initial = params.get("q") ?? "";
  const [q, setQ] = useState(initial);
  const [city, setCity] = useState("");
  const [activeFilters, setActiveFilters] = useState({ q: initial, city: "" });
  const [results, setResults] = useState<User[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(Boolean(initial));
  const [error, setError] = useState("");

  async function request(filters: { q: string; city: string }, cursor: string | null, append: boolean) {
    setLoading(true); setError("");
    try {
      const page = await usersApi.search(filters.q, filters.city || undefined, { cursor });
      setResults((current) => append ? [...current, ...page.items] : page.items);
      setNextCursor(page.next_cursor); setHasMore(page.has_more);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo buscar"); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    if (!initial) return;
    const filters = { q: initial.trim(), city: "" };
    let active = true;
    usersApi.search(filters.q).then((page) => {
      if (!active) return;
      setResults(page.items); setNextCursor(page.next_cursor); setHasMore(page.has_more);
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "No se pudo buscar");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [initial]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const filters = { q: q.trim(), city: city.trim() };
    if (!filters.q) return;
    setActiveFilters(filters); setNextCursor(null); setHasMore(false);
    void request(filters, null, false);
  }

  return <><form onSubmit={submit} className="card search-filters"><label>Palabras clave<input required value={q} onChange={(event) => setQ(event.target.value)} placeholder="Nombre, titular o puesto"/></label><label>Ciudad<input value={city} onChange={(event) => setCity(event.target.value)} placeholder="Opcional"/></label><button className="primary-button">Buscar</button></form><section className="card results-section"><h1>Resultados de personas</h1>{error && <p className="inline-error">{error}</p>}{loading && !results.length ? <div className="skeleton result-skeleton"/> : results.length ? <><div className="people-grid search-people">{results.map((person) => <PersonCard key={person.id} person={person}/>)}</div>{hasMore && <button type="button" className="secondary-button" disabled={loading} onClick={() => void request(activeFilters, nextCursor, true)}>{loading ? "Cargando..." : "Cargar más"}</button>}</> : <div className="empty-state">No encontramos personas con esos criterios.</div>}</section></>;
}

export default function SearchPage() { return <AppShell><main className="app-background"><div className="single-column"><Suspense fallback={<div className="card skeleton result-skeleton"/>}><SearchResults/></Suspense></div></main></AppShell>; }
