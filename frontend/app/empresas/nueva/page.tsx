"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { companiesApi } from "@/lib/api";

export default function NewCompanyPage() {
  const router = useRouter(); const [data, setData] = useState({ nombre: "", industria: "", sitio_web: "" }); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setError(""); try { const company = await companiesApi.create({ nombre: data.nombre, industria: data.industria || null, sitio_web: data.sitio_web || null }); router.push(`/empresas/${company.id}`); } catch (err) { setError(err instanceof Error ? err.message : "No se pudo crear la empresa"); } finally { setBusy(false); } }
  return <AppShell><main className="app-background"><div className="single-column narrow"><section className="card entity-form"><h1>Crear una página de empresa</h1><p>Al crearla quedarás asociado como OWNER.</p><form onSubmit={submit}><label>Nombre<input required maxLength={100} value={data.nombre} onChange={(e) => setData({ ...data, nombre: e.target.value })}/></label><label>Industria<input maxLength={100} value={data.industria} onChange={(e) => setData({ ...data, industria: e.target.value })}/></label><label>Sitio web<input type="url" placeholder="https://" value={data.sitio_web} onChange={(e) => setData({ ...data, sitio_web: e.target.value })}/></label>{error && <p className="inline-error">{error}</p>}<button disabled={busy} className="primary-button">{busy ? "Creando..." : "Crear empresa"}</button></form></section></div></main></AppShell>;
}
