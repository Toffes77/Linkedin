"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Icon } from "@/components/common/icons";
import {
  companiesApi,
  jobsApi,
  type Application,
  type Company,
  type Job,
} from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function JobsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [companies, setCompanies] = useState<Record<number, Company>>({});
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobsCursor, setJobsCursor] = useState<string | null>(null);
  const [jobsHasMore, setJobsHasMore] = useState(false);
  const [applicationsCursor, setApplicationsCursor] = useState<string | null>(null);
  const [applicationsHasMore, setApplicationsHasMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [applicationsError, setApplicationsError] = useState("");

  useEffect(() => {
    if (!user) return;

    let active = true;
    jobsApi
      .applicationsByUser(user.id)
      .then((page) => {
        if (active) { setApplications(page.items); setApplicationsCursor(page.next_cursor); setApplicationsHasMore(page.has_more); }
      })
      .catch((cause) => {
        if (active) {
          setApplicationsError(
            cause instanceof Error
              ? cause.message
              : "No se pudieron cargar tus postulaciones",
          );
        }
      });

    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => {
    if (!user) return;

    const query = searchQuery.trim();
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(
      () => {
        setError("");
        setLoading(true);

        jobsApi
          .published(query || undefined, { signal: controller.signal })
          .then(async (page) => {
            const offers = page.items;
            const companyIds = [
              ...new Set(offers.map((item) => item.empresa_id)),
            ];
            const companyList = companyIds.length
              ? await companiesApi.getBatch(companyIds)
              : [];

            if (!active) return;
            setJobs(offers);
            setJobsCursor(page.next_cursor);
            setJobsHasMore(page.has_more);
            setCompanies(
              Object.fromEntries(
                companyList
                  .map((company) => [company.id, company]),
              ),
            );
          })
          .catch((cause) => {
            if (!active || cause instanceof DOMException && cause.name === "AbortError") {
              return;
            }
            setJobs([]);
            setError(
              cause instanceof Error
                ? cause.message
                : "No se pudieron cargar empleos",
            );
          })
          .finally(() => {
            if (active) setLoading(false);
          });
      },
      query ? 300 : 0,
    );

    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [searchQuery, user]);

  const activeSearch = searchQuery.trim().length > 0;

  async function loadMoreJobs() {
    const page = await jobsApi.published(searchQuery.trim() || undefined, { cursor: jobsCursor });
    const missingCompanyIds = [...new Set(page.items.map((item) => item.empresa_id))]
      .filter((id) => !companies[id]);
    const loadedCompanies = missingCompanyIds.length
      ? await companiesApi.getBatch(missingCompanyIds)
      : [];
    setCompanies((current) => ({
      ...current,
      ...Object.fromEntries(loadedCompanies.map((company) => [company.id, company])),
    }));
    setJobs((current) => [...current, ...page.items]); setJobsCursor(page.next_cursor); setJobsHasMore(page.has_more);
  }

  async function loadMoreApplications() {
    if (!user) return;
    const page = await jobsApi.applicationsByUser(user.id, { cursor: applicationsCursor });
    setApplications((current) => [...current, ...page.items]); setApplicationsCursor(page.next_cursor); setApplicationsHasMore(page.has_more);
  }

  return (
    <AppShell>
      <main className="app-background">
        <div className="jobs-layout">
          <aside className="card jobs-sidebar">
            <h2>Empleos</h2>
            <div className="jobs-search">
              <label className="jobs-search-control" htmlFor="job-title-search">
                <Icon name="search" className="jobs-search-icon" />
                <span className="sr-only">Buscar empleos</span>
                <input
                  id="job-title-search"
                  type="search"
                  value={searchQuery}
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    setLoading(true);
                  }}
                  placeholder="Buscar"
                  autoComplete="off"
                />
              </label>
            </div>
            <a href="#offers">Buscar empleos</a>
            <a href="#applications">Mis postulaciones</a>
            <Link href="/empresas/nueva">Crear una empresa</Link>
          </aside>
          <div>
            <section id="offers" className="card jobs-list" aria-busy={loading}>
              <h1>Principales ofertas para vos</h1>
              {error ? (
                <p className="inline-error">{error}</p>
              ) : loading ? (
                <div className="skeleton result-skeleton" />
              ) : jobs.length ? (
                jobs.map((job) => (
                  <Link
                    href={`/empleos/${job.id}`}
                    className="job-list-item"
                    key={job.id}
                  >
                    <span className="company-placeholder">
                      {companies[job.empresa_id]?.nombre[0] ?? "E"}
                    </span>
                    <div>
                      <h2>{job.titulo}</h2>
                      <strong>
                        {companies[job.empresa_id]?.nombre ??
                          `Empresa ${job.empresa_id}`}
                      </strong>
                      <p>{job.descripcion}</p>
                      <small>{formatDate(job.fecha_publicacion)}</small>
                    </div>
                  </Link>
                ))
              ) : (
                <div className="empty-state">
                  {activeSearch
                    ? "No se encontraron ofertas para esta búsqueda."
                    : "No hay ofertas publicadas."}
                </div>
              )}
              {jobsHasMore && !loading && <button type="button" className="secondary-button" onClick={() => void loadMoreJobs()}>Cargar más ofertas</button>}
            </section>
            <section id="applications" className="card jobs-list applications">
              <h2>Mis postulaciones</h2>
              {applicationsError && (
                <p className="inline-error">{applicationsError}</p>
              )}
              {applications.length ? (
                applications.map((item) => (
                  <Link href={`/empleos/${item.oferta_id}`} key={item.id}>
                    <strong>{item.oferta_titulo}</strong>
                    <span className={`status status-${item.estado}`}>
                      {item.estado}
                    </span>
                    <small>{formatDate(item.fecha)}</small>
                  </Link>
                ))
              ) : !applicationsError ? (
                <p className="muted">
                  Todavía no te postulaste a ninguna oferta.
                </p>
              ) : null}
              {applicationsHasMore && <button type="button" className="secondary-button" onClick={() => void loadMoreApplications()}>Cargar más postulaciones</button>}
            </section>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
