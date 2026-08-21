"use client";

import { FormEvent, use, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { companiesApi, type Company } from "@/lib/api";

export default function EditCompanyPage({ params }: { params: Promise<{ id: string }> }) {
  const id = Number(use(params).id); const [company, setCompany] = useState<Company | null>(null); const [photo, setPhoto] = useState<File | null>(null); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { companiesApi.get(id).then(setCompany).catch((e) => setMessage(e instanceof Error ? e.message : "No se pudo cargar")); }, [id]);
  async function save(e: FormEvent) { e.preventDefault(); if (!company) return; setBusy(true); setMessage(""); try { let updated = await companiesApi.update(id, { nombre: company.nombre, industria: company.industria, sitio_web: company.sitio_web }); if (photo) updated = await companiesApi.photo(id, photo); setCompany(updated); setMessage("Empresa actualizada correctamente."); } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudo actualizar"); } finally { setBusy(false); } }
  return <AppShell><main className="app-background"><div className="single-column narrow"><section className="card entity-form"><h1>Editar empresa</h1>{company && <form onSubmit={save}><label>Nombre<input required value={company.nombre} onChange={(e) => setCompany({ ...company, nombre: e.target.value })}/></label><label>Industria<input value={company.industria ?? ""} onChange={(e) => setCompany({ ...company, industria: e.target.value || null })}/></label><label>Sitio web<input type="url" value={company.sitio_web ?? ""} onChange={(e) => setCompany({ ...company, sitio_web: e.target.value || null })}/></label><label>Logo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}/></label>{message && <p>{message}</p>}<button className="primary-button" disabled={busy}>{busy ? "Guardando..." : "Guardar cambios"}</button></form>}</section></div></main></AppShell>;
}
