"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { companiesApi, jobsApi, type Application, type Company, type Job } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function JobsPage() {
  const { user } = useAuth(); const [jobs, setJobs] = useState<Job[]>([]); const [companies, setCompanies] = useState<Record<number, Company>>({}); const [applications, setApplications] = useState<Application[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!user) return; Promise.all([jobsApi.published(), jobsApi.applicationsByUser(user.id)]).then(async ([offers, applied]) => { setJobs(offers); setApplications(applied); const ids = [...new Set(offers.map((item) => item.empresa_id))]; const list = await Promise.all(ids.map((id) => companiesApi.get(id).catch(() => null))); setCompanies(Object.fromEntries(list.filter((company): company is Company => company !== null).map((company) => [company.id, company]))); }).catch((e) => setError(e instanceof Error ? e.message : "No se pudieron cargar empleos")).finally(() => setLoading(false)); }, [user]);
  return <AppShell><main className="app-background"><div className="jobs-layout"><aside className="card jobs-sidebar"><h2>Empleos</h2><a href="#offers">Buscar empleos</a><a href="#applications">Mis postulaciones</a><Link href="/empresas/nueva">Crear una empresa</Link></aside><div><section id="offers" className="card jobs-list"><h1>Principales ofertas para vos</h1>{error && <p className="inline-error">{error}</p>}{loading ? <div className="skeleton result-skeleton"/> : jobs.length ? jobs.map((job) => <Link href={`/empleos/${job.id}`} className="job-list-item" key={job.id}><span className="company-placeholder">{companies[job.empresa_id]?.nombre[0] ?? "E"}</span><div><h2>{job.titulo}</h2><strong>{companies[job.empresa_id]?.nombre ?? `Empresa ${job.empresa_id}`}</strong><p>{job.descripcion}</p><small>{formatDate(job.fecha_publicacion)}</small></div></Link>) : <div className="empty-state">No hay ofertas publicadas.</div>}</section><section id="applications" className="card jobs-list applications"><h2>Mis postulaciones</h2>{applications.length ? applications.map((item) => <Link href={`/empleos/${item.oferta_id}`} key={item.id}><strong>{item.oferta_titulo}</strong><span className={`status status-${item.estado}`}>{item.estado}</span><small>{formatDate(item.fecha)}</small></Link>) : <p className="muted">Todavía no te postulaste a ninguna oferta.</p>}</section></div></div></main></AppShell>;
}
