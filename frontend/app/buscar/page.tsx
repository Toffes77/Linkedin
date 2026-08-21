"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { PersonCard } from "@/components/network/person-card";
import { usersApi, type User } from "@/lib/api";

function SearchResults() {
  const params = useSearchParams(); const initial = params.get("q") ?? ""; const [q, setQ] = useState(initial); const [city, setCity] = useState(""); const [results, setResults] = useState<User[]>([]); const [loading, setLoading] = useState(Boolean(initial)); const [error, setError] = useState("");
  async function run(query = q, ciudad = city) { if (!query.trim()) return; setLoading(true); setError(""); try { setResults(await usersApi.search(query.trim(), ciudad.trim() || undefined)); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo buscar"); } finally { setLoading(false); } }
  useEffect(() => { if (!initial) return; let active = true; usersApi.search(initial).then((items) => { if (active) setResults(items); }).catch((e) => { if (active) setError(e instanceof Error ? e.message : "No se pudo buscar"); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [initial]);
  function submit(e: FormEvent) { e.preventDefault(); void run(); }
  return <><form onSubmit={submit} className="card search-filters"><label>Palabras clave<input required value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre, titular o puesto"/></label><label>Ciudad<input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Opcional"/></label><button className="primary-button">Buscar</button></form><section className="card results-section"><h1>Resultados de personas</h1>{error && <p className="inline-error">{error}</p>}{loading ? <div className="skeleton result-skeleton"/> : results.length ? <div className="people-grid search-people">{results.map((person) => <PersonCard key={person.id} person={person}/>)}</div> : <div className="empty-state">No encontramos personas con esos criterios.</div>}</section></>;
}
export default function SearchPage() { return <AppShell><main className="app-background"><div className="single-column"><Suspense fallback={<div className="card skeleton result-skeleton"/>}><SearchResults/></Suspense></div></main></AppShell>; }
