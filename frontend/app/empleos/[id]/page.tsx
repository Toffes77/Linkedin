"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";
import { CompanyLogo } from "@/components/companies/company-logo";
import { companiesApi, jobsApi, type Application, type Company, type CompanyRole, type Job, type JobStats } from "@/lib/api";
import { formatDateArgentina } from "@/lib/format";
import { getJobApplicationActionState, type MembershipCheckState } from "@/lib/job-application-state";

export default function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const id = Number(use(params).id);
  const { user, loading: authLoading } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [membershipResult, setMembershipResult] = useState<{
    offerId: number;
    status: Exclude<MembershipCheckState, "loading">;
    role: CompanyRole | undefined;
  } | null>(null);
  const [applied, setApplied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [stats, setStats] = useState<JobStats | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [applicationsCursor, setApplicationsCursor] = useState<string | null>(null);
  const [applicationsHasMore, setApplicationsHasMore] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    let active = true;
    jobsApi.get(id).then(async (loaded) => {
      const [loadedCompany, mine, myApplications] = await Promise.all([
        companiesApi.get(loaded.empresa_id),
        user ? companiesApi.mine() : Promise.resolve([]),
        user
          ? jobsApi.applicationsByUser(user.id, { offerId: id, limit: 1 }).catch(() => ({ items: [], next_cursor: null, has_more: false }))
          : Promise.resolve({ items: [], next_cursor: null, has_more: false }),
      ]);
      if (!active) return;
      setJob(loaded);
      setCompany(loadedCompany);
      setApplied(myApplications.items.length > 0);
      setMembershipResult({
        offerId: id,
        status: "ready",
        role: mine.find((item) => item.empresa.id === loaded.empresa_id)?.rol,
      });
    }).catch((cause) => {
      if (active) {
        setMembershipResult({ offerId: id, status: "error", role: undefined });
        setMessage(cause instanceof Error ? cause.message : "No se pudo cargar la oferta");
      }
    });
    return () => {
      active = false;
    };
  }, [id, user, authLoading]);

  const membershipCheck: MembershipCheckState = membershipResult?.offerId === id
    ? membershipResult.status
    : "loading";
  const myRole = membershipResult?.offerId === id && membershipResult.status === "ready"
    ? membershipResult.role
    : undefined;

  async function apply() {
    if (!user || membershipCheck !== "ready" || myRole !== undefined) return;
    setBusy(true); setMessage("");
    try { await jobsApi.apply(id); setApplied(true); setMessage("Postulación enviada correctamente."); }
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
  const applicationAction = getJobApplicationActionState({
    membershipCheck,
    role: myRole,
    applied,
    busy,
  });
  return <AppShell><main className="app-background"><div className="single-column">{job && <>
    <section className="card job-detail"><CompanyLogo name={company?.nombre ?? "Empresa"} src={company?.foto_perfil_url} className="company-placeholder large"/><h1>{job.titulo}</h1>{company && <Link href={`/empresas/${company.id}`}>{company.nombre}</Link>}<p>{company?.industria} · Publicada {formatDateArgentina(job.fecha_publicacion)}</p>{applicationAction.membershipMessage ? <p className="standalone-message">{applicationAction.membershipMessage}</p> : applicationAction.showButton && <button onClick={apply} disabled={applicationAction.disabled} className="primary-button">{applicationAction.label}</button>}{message && <p className="standalone-message" role="alert">{message}</p>}</section>
    <section className="card profile-section"><h2>Acerca del empleo</h2><p className="job-description">{job.descripcion}</p></section>
    {canManageJob && <section className="card profile-section management"><h2>Administración de la oferta</h2><p>Solo los OWNER y RECRUITER de la empresa pueden acceder a esta sección.</p><button onClick={loadManagement} className="secondary-button">Ver estadísticas y postulantes</button>{stats && <div className="stats-row"><strong>{stats.total_postulaciones}</strong> postulaciones · {stats.dias_desde_publicacion ?? 0} días publicada</div>}{applications?.map((application) => <div className="application-row" key={application.id}><Link href={`/perfil/${application.postulante.id}`} className="application-row-applicant"><Avatar name={application.postulante.nombre} src={application.postulante.foto_perfil_url} size={42}/><span>{application.postulante.nombre}</span></Link><span>{application.estado}</span><select value={application.estado} onChange={(event) => updateApplication(application, event.target.value as Application["estado"])}><option value={application.estado}>{application.estado}</option>{application.estado === "nueva" && <><option value="vista">vista</option><option value="rechazada">rechazada</option></>}{application.estado === "vista" && <><option value="entrevista">entrevista</option><option value="rechazada">rechazada</option></>}{application.estado === "entrevista" && <><option value="contratado">contratado</option><option value="rechazada">rechazada</option></>}</select></div>)}{applicationsHasMore && <button type="button" className="secondary-button" onClick={() => void loadMoreApplications()}>Cargar más postulantes</button>}</section>}
  </>}</div></main></AppShell>;
}
