"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { companiesApi, jobsApi, type Application, type Company, type CompanyRole, type Job, type JobStats } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const id = Number(use(params).id);
  const { user } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [myRole, setMyRole] = useState<CompanyRole | undefined>();
  const [applied, setApplied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [stats, setStats] = useState<JobStats | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [applicationsCursor, setApplicationsCursor] = useState<string | null>(null);
  const [applicationsHasMore, setApplicationsHasMore] = useState(false);

  useEffect(() => {
    jobsApi.get(id).then(async (loaded) => {
      setJob(loaded);
      setCompany(await companiesApi.get(loaded.empresa_id));
      if (user) {
        const [mine, myApplications] = await Promise.all([
          companiesApi.mine().catch(() => []),
          jobsApi.applicationsByUser(user.id, { offerId: id, limit: 1 }).catch(() => ({ items: [], next_cursor: null, has_more: false })),
        ]);
        setMyRole(mine.find((item) => item.empresa.id === loaded.empresa_id)?.rol);
        setApplied(myApplications.items.length > 0);
      } else setMyRole(undefined);
    }).catch((cause) => setMessage(cause instanceof Error ? cause.message : "No se pudo cargar la oferta"));
  }, [id, user]);

  async function apply() {
    if (!user) return;
    setBusy(true); setMessage("");
    try { await jobsApi.apply(id, user.id); setApplied(true); setMessage("Postulación enviada correctamente."); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "No se pudo enviar la postulación"); }
    finally { setBusy(false); }
  }

  async function loadManagement() {
    setMessage("");
    try {
      const [loadedStats, page] = await Promise.all([jobsApi.stats(id), jobsApi.applicationsByJob(id)]);
      setStats(loadedStats); setApplications(page.items); setApplicationsCursor(page.next_cursor); setApplicationsHasMore(page.has_more);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "No tenés permisos para administrar esta oferta"); }
  }

  async function loadMoreApplications() {
    const page = await jobsApi.applicationsByJob(id, applicationsCursor);
    setApplications((current) => [...(current ?? []), ...page.items]); setApplicationsCursor(page.next_cursor); setApplicationsHasMore(page.has_more);
  }

  async function updateApplication(application: Application, estado: Application["estado"]) {
    try {
      const updated = await jobsApi.updateApplication(application.id, estado);
      setApplications((current) => current?.map((item) => item.id === updated.id ? updated : item) ?? null);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "No se pudo actualizar"); }
  }

  const canManageJob = myRole === "OWNER" || myRole === "RECRUITER";
  return <AppShell><main className="app-background"><div className="single-column">{job && <>
    <section className="card job-detail"><span className="company-placeholder large">{company?.nombre[0] ?? "E"}</span><h1>{job.titulo}</h1>{company && <Link href={`/empresas/${company.id}`}>{company.nombre}</Link>}<p>{company?.industria} · Publicada {formatDate(job.fecha_publicacion)}</p><button onClick={apply} disabled={busy || applied} className="primary-button">{busy ? "Enviando..." : applied ? "Ya te postulaste" : "Postularme"}</button>{message && <p className="standalone-message">{message}</p>}</section>
    <section className="card profile-section"><h2>Acerca del empleo</h2><p className="job-description">{job.descripcion}</p></section>
    {canManageJob && <section className="card profile-section management"><h2>Administración de la oferta</h2><p>Disponible para OWNER o RECRUITER. FastAPI valida el permiso.</p><button onClick={loadManagement} className="secondary-button">Ver estadísticas y postulantes</button>{stats && <div className="stats-row"><strong>{stats.total_postulaciones}</strong> postulaciones · {stats.dias_desde_publicacion ?? 0} días publicada</div>}{applications?.map((application) => <div className="application-row" key={application.id}><Link href={`/perfil/${application.usuario_id}`}>Usuario {application.usuario_id}</Link><span>{application.estado}</span><select value={application.estado} onChange={(event) => updateApplication(application, event.target.value as Application["estado"])}><option value={application.estado}>{application.estado}</option>{application.estado === "nueva" && <><option value="vista">vista</option><option value="rechazada">rechazada</option></>}{application.estado === "vista" && <><option value="entrevista">entrevista</option><option value="rechazada">rechazada</option></>}{application.estado === "entrevista" && <><option value="contratado">contratado</option><option value="rechazada">rechazada</option></>}</select></div>)}{applicationsHasMore && <button type="button" className="secondary-button" onClick={() => void loadMoreApplications()}>Cargar más postulantes</button>}</section>}
  </>}</div></main></AppShell>;
}
