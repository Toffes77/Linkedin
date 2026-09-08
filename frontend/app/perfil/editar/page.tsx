"use client";

import Image from "next/image";
import { FormEvent, use, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Alert } from "@/components/common/alert";
import { CityAutocomplete } from "@/components/profile/city-autocomplete";
import { CompanySelector } from "@/components/profile/company-selector";
import { companiesApi, mediaUrl, usersApi, type Company, type Experience } from "@/lib/api";
import { getLocalDateForInput, validateExperienceDates } from "@/lib/experience-dates";

type Message = { text: string; success: boolean } | null;
type ExperienceForm = {
  empresa_id: number | null;
  puesto: string;
  desde: string;
  hasta: string;
};

const emptyExperience = (): ExperienceForm => ({
  empresa_id: null,
  puesto: "",
  desde: "",
  hasta: "",
});

export default function EditProfilePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string | string[] }>;
}) {
  const requestedTab = use(searchParams).tab;
  const initialTab = requestedTab === "experience" ? "experience" : "profile";
  const { user, refreshUser } = useAuth();
  const [tab, setTab] = useState<"profile" | "photo" | "password" | "experience">(initialTab);
  const [profile, setProfile] = useState<{ nombre: string; headline: string } | null>(null);
  const [selectedCity, setSelectedCity] = useState<string | null | undefined>(undefined);
  const [cityError, setCityError] = useState("");
  const [message, setMessage] = useState<Message>(null);
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [experience, setExperience] = useState<ExperienceForm>(emptyExperience);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [experienceCompanies, setExperienceCompanies] = useState<Record<number, Company>>({});
  const [companySelectorKey, setCompanySelectorKey] = useState(0);
  const [editingExperienceId, setEditingExperienceId] = useState<number | null>(null);
  const [deletingExperienceId, setDeletingExperienceId] = useState<number | null>(null);
  const [experienceActionBusyId, setExperienceActionBusyId] = useState<number | null>(null);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  useEffect(() => {
    if (!user) return;
    const companyIds = [...new Set(user.experiencias.map((item) => item.empresa_id))];
    let active = true;
    if (!companyIds.length) {
      Promise.resolve().then(() => {
        if (active) setExperienceCompanies({});
      });
      return () => {
        active = false;
      };
    }
    companiesApi.getBatch(companyIds)
      .then((companies) => {
        if (active) setExperienceCompanies(Object.fromEntries(companies.map((company) => [company.id, company])));
      })
      .catch(() => {
        if (active) setExperienceCompanies({});
      });
    return () => {
      active = false;
    };
  }, [user]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setMessage(null);
    const city = selectedCity === undefined ? user.ciudad : selectedCity;
    if (!city) {
      setCityError("Seleccioná una ciudad de la lista.");
      return;
    }
    setBusy(true);
    try {
      await usersApi.update({ ...(profile ?? { nombre: user.nombre, headline: user.headline }), ciudad: city });
      await refreshUser();
      setMessage({ text: "Perfil actualizado correctamente.", success: true });
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "No se pudo actualizar", success: false });
    } finally {
      setBusy(false);
    }
  }

  function choosePhoto(file: File | null) {
    if (preview) URL.revokeObjectURL(preview);
    setPhoto(file);
    setPreview(file ? URL.createObjectURL(file) : null);
  }

  async function uploadPhoto(e: FormEvent) {
    e.preventDefault();
    if (!photo) return;
    setBusy(true);
    setMessage(null);
    try {
      await usersApi.photo(photo);
      await refreshUser();
      setMessage({ text: "Foto actualizada correctamente.", success: true });
      setPhoto(null);
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "No se pudo subir la foto", success: false });
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (passwords.next !== passwords.confirm) {
      setMessage({ text: "Las contraseñas nuevas no coinciden.", success: false });
      return;
    }
    setBusy(true);
    try {
      const result = await usersApi.password(passwords.current, passwords.next);
      setMessage({ text: result.message, success: true });
      setPasswords({ current: "", next: "", confirm: "" });
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "No se pudo cambiar la contraseña", success: false });
    } finally {
      setBusy(false);
    }
  }

  function resetExperienceForm() {
    setEditingExperienceId(null);
    setDeletingExperienceId(null);
    setExperience(emptyExperience());
    setSelectedCompany(null);
    setCompanySelectorKey((key) => key + 1);
  }

  function companyForExperience(companyId: number): Company {
    return experienceCompanies[companyId] ?? {
      id: companyId,
      nombre: `Empresa #${companyId}`,
      industria: null,
      sitio_web: null,
      foto_perfil_url: null,
    };
  }

  function beginExperienceEdit(item: Experience) {
    setTab("experience");
    setMessage(null);
    setDeletingExperienceId(null);
    setEditingExperienceId(item.id);
    setExperience({
      empresa_id: item.empresa_id,
      puesto: item.puesto,
      desde: item.desde,
      hasta: item.hasta ?? "",
    });
    setSelectedCompany(companyForExperience(item.empresa_id));
    setCompanySelectorKey((key) => key + 1);
  }

  async function saveExperience(e: FormEvent) {
    e.preventDefault();
    if (!user || experience.empresa_id === null) {
      setMessage({ text: "Seleccioná una empresa de los resultados.", success: false });
      return;
    }
    const dateError = validateExperienceDates(experience, getLocalDateForInput());
    if (dateError) {
      setMessage({ text: dateError, success: false });
      return;
    }
    setBusy(true);
    setMessage(null);
    const payload = {
      empresa_id: experience.empresa_id,
      puesto: experience.puesto,
      desde: experience.desde,
      hasta: experience.hasta || null,
    };
    try {
      if (editingExperienceId === null) {
        await usersApi.addExperience(user.id, payload);
        setMessage({ text: "Experiencia agregada correctamente.", success: true });
      } else {
        await usersApi.updateExperience(editingExperienceId, payload);
        setMessage({ text: "Experiencia actualizada correctamente.", success: true });
      }
      await refreshUser();
      resetExperienceForm();
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "No se pudo guardar la experiencia", success: false });
    } finally {
      setBusy(false);
    }
  }

  async function deleteExperience(experienceId: number) {
    setExperienceActionBusyId(experienceId);
    setMessage(null);
    try {
      await usersApi.deleteExperience(experienceId);
      if (editingExperienceId === experienceId) resetExperienceForm();
      await refreshUser();
      setMessage({ text: "Experiencia eliminada correctamente.", success: true });
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "No se pudo eliminar la experiencia", success: false });
    } finally {
      setExperienceActionBusyId(null);
      setDeletingExperienceId(null);
    }
  }

  if (!user) return null;
  const profileValues = profile ?? { nombre: user.nombre, headline: user.headline };
  const profileCity = selectedCity === undefined ? user.ciudad : selectedCity;
  const editing = editingExperienceId !== null;
  const maxExperienceDate = getLocalDateForInput();

  return <AppShell><main className="app-background"><div className="settings-layout"><aside className="card settings-nav"><h1>Ajustes del perfil</h1>{([["profile", "Información personal"], ["photo", "Foto de perfil"], ["password", "Cambiar contraseña"], ["experience", "Experiencias"]] as const).map(([key, label]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => { setTab(key); setMessage(null); }}>{label}</button>)}</aside><section className="card settings-panel">{message && <Alert success={message.success}>{message.text}</Alert>}
    {tab === "profile" && <form onSubmit={saveProfile}><h2>Editar presentación</h2><label>Nombre<input required maxLength={100} value={profileValues.nombre} onChange={(e) => setProfile({ ...profileValues, nombre: e.target.value })}/></label><label>Titular<input required maxLength={200} value={profileValues.headline} onChange={(e) => setProfile({ ...profileValues, headline: e.target.value })}/></label><CityAutocomplete selectedCity={profileCity} onSelect={(city) => { setSelectedCity(city); if (city) setCityError(""); }} validationError={cityError} disabled={busy}/><button disabled={busy} className="primary-button">{busy ? "Guardando..." : "Guardar"}</button></form>}
    {tab === "photo" && <form onSubmit={uploadPhoto}><h2>Foto de perfil</h2><div className="photo-preview">{preview || mediaUrl(user.foto_perfil_url) ? <Image unoptimized src={preview ?? mediaUrl(user.foto_perfil_url)!} alt="Vista previa" width={180} height={180}/> : <span>{user.nombre[0]}</span>}</div><label>Seleccionar imagen<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}/></label><button disabled={busy || !photo} className="primary-button">{busy ? "Subiendo..." : "Guardar foto"}</button></form>}
    {tab === "password" && <form onSubmit={changePassword}><h2>Cambiar contraseña</h2><label>Contraseña actual<input type="password" required value={passwords.current} onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}/></label><label>Nueva contraseña<input type="password" minLength={8} required value={passwords.next} onChange={(e) => setPasswords({ ...passwords, next: e.target.value })}/></label><label>Confirmar nueva contraseña<input type="password" minLength={8} required value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}/></label><button disabled={busy} className="primary-button">{busy ? "Actualizando..." : "Cambiar contraseña"}</button></form>}
    {tab === "experience" && <>
      <form id="experiencias" onSubmit={saveExperience}><h2>{editing ? "Editar experiencia" : "Añadir experiencia"}</h2><p className="form-help">Buscá la empresa por nombre y elegila de los resultados.</p><CompanySelector key={companySelectorKey} selected={selectedCompany} onSelect={(company) => { setSelectedCompany(company); setExperience({ ...experience, empresa_id: company?.id ?? null }); }}/><label>Puesto<input required maxLength={100} value={experience.puesto} onChange={(e) => setExperience({ ...experience, puesto: e.target.value })}/></label><label>Desde<input type="date" required max={maxExperienceDate} value={experience.desde} onChange={(e) => setExperience({ ...experience, desde: e.target.value })} onInvalid={(e) => { if (e.currentTarget.validity.rangeOverflow) setMessage({ text: "La fecha de inicio no puede ser posterior a hoy.", success: false }); }}/></label><label>Hasta (opcional)<input type="date" max={maxExperienceDate} value={experience.hasta} onChange={(e) => setExperience({ ...experience, hasta: e.target.value })} onInvalid={(e) => { if (e.currentTarget.validity.rangeOverflow) setMessage({ text: "La fecha de finalización no puede ser posterior a hoy.", success: false }); }}/></label><div className="experience-form-actions"><button disabled={busy || experience.empresa_id === null} className="primary-button">{busy ? "Guardando..." : editing ? "Guardar cambios" : "Añadir experiencia"}</button>{editing && <button type="button" className="text-button" onClick={resetExperienceForm} disabled={busy}>Cancelar edición</button>}</div></form>
      <section className="profile-edit-experiences" aria-labelledby="experiencias-actuales"><h2 id="experiencias-actuales">Experiencias actuales</h2>{user.experiencias.length ? user.experiencias.map((item) => <article className="experience-row" key={item.id}><span className="company-placeholder">{companyForExperience(item.empresa_id).nombre.slice(0, 1)}</span><div className="experience-row-content"><h3>{item.puesto}</h3><span>{companyForExperience(item.empresa_id).nombre}</span><p>{item.desde} – {item.hasta ?? "Actualidad"}</p><div className="experience-actions"><button type="button" className="text-button" onClick={() => beginExperienceEdit(item)} disabled={busy || experienceActionBusyId !== null}>Editar</button>{deletingExperienceId === item.id ? <div className="experience-delete-confirm" role="alert"><span>¿Eliminar esta experiencia?</span><button type="button" className="text-button" onClick={() => setDeletingExperienceId(null)} disabled={experienceActionBusyId === item.id}>Cancelar</button><button type="button" className="danger-button" onClick={() => void deleteExperience(item.id)} disabled={experienceActionBusyId === item.id}>{experienceActionBusyId === item.id ? "Eliminando..." : "Eliminar"}</button></div> : <button type="button" className="text-button" onClick={() => { setMessage(null); setDeletingExperienceId(item.id); }} disabled={busy || experienceActionBusyId !== null}>Eliminar</button>}</div></div></article>) : <p className="muted">Todavía no agregaste experiencias.</p>}</section>
    </>}
  </section></div></main></AppShell>;
}
