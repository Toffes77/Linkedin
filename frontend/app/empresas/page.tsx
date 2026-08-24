"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { CompanyCard } from "@/components/companies/company-card";
import { Icon } from "@/components/common/icons";
import { companiesApi, type Company, type MyCompany } from "@/lib/api";

export default function CompaniesPage() {
  const [mine, setMine] = useState<MyCompany[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    companiesApi.mine().then((items) => { if (active) setMine(items); }).catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "No se pudieron cargar tus empresas."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const owners = useMemo(() => mine.filter((item) => item.rol === "OWNER"), [mine]);
  const recruiters = useMemo(() => mine.filter((item) => item.rol === "RECRUITER"), [mine]);
  const collaborators = useMemo(() => mine.filter((item) => item.rol === "COLLABORATOR"), [mine]);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) { setResults(null); return; }
    setSearching(true); setError("");
    try { setResults(await companiesApi.search(query.trim())); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "No se pudo realizar la búsqueda."); }
    finally { setSearching(false); }
  }

  return <AppShell><main className="app-background"><div className="companies-page">
    <section className="card companies-heading"><div><h1>Empresas</h1><p>Encontrá empresas y administrá aquellas en las que participás.</p></div><Link href="/empresas/nueva" className="primary-button">Crear empresa</Link></section>
    <form className="card company-search" onSubmit={search}><Icon name="search"/><label className="sr-only" htmlFor="company-search">Buscar empresas por nombre</label><input id="company-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar empresas por nombre"/><button className="primary-button" disabled={searching}>{searching ? "Buscando..." : "Buscar"}</button>{results !== null && <button type="button" className="text-button" onClick={() => { setQuery(""); setResults(null); }}>Limpiar</button>}</form>
    {error && <div className="notice notice-error">{error}</div>}
    {results !== null ? <section className="card company-group"><header><h2>Resultados de búsqueda</h2><span>{results.length} {results.length === 1 ? "empresa" : "empresas"}</span></header>{results.length ? <div className="company-card-grid">{results.map((company) => <CompanyCard company={company} key={company.id}/>)}</div> : <div className="company-empty">No se encontraron empresas.</div>}</section> : loading ? <div className="company-loading"><div className="card skeleton"/><div className="card skeleton"/></div> : <>
      <section className="card company-group"><header><div><span className="role-mark owner-mark">O</span><div><h2>Propietario</h2><p>Empresas que administrás como OWNER</p></div></div><span>{owners.length}</span></header>{owners.length ? <div className="company-card-grid">{owners.map(({ empresa }) => <CompanyCard company={empresa} key={empresa.id}/>)}</div> : <div className="company-empty">No administrás ninguna empresa actualmente.</div>}</section>
      <section className="card company-group"><header><div><span className="role-mark recruiter-mark">R</span><div><h2>Recruiter</h2><p>Empresas a las que pertenecés como RECRUITER</p></div></div><span>{recruiters.length}</span></header>{recruiters.length ? <div className="company-card-grid">{recruiters.map(({ empresa }) => <CompanyCard company={empresa} key={empresa.id}/>)}</div> : <div className="company-empty">No pertenecés como recruiter a ninguna empresa.</div>}</section>
      <section className="card company-group"><header><div><span className="role-mark collaborator-mark">C</span><div><h2>Colaborador</h2><p>Empresas a las que pertenecés como colaborador</p></div></div><span>{collaborators.length}</span></header>{collaborators.length ? <div className="company-card-grid">{collaborators.map(({ empresa }) => <CompanyCard company={empresa} key={empresa.id}/>)}</div> : <div className="company-empty">No pertenecés como colaborador a ninguna empresa.</div>}</section>
    </>}
  </div></main></AppShell>;
}
