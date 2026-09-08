"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { CityAutocomplete } from "@/components/profile/city-autocomplete";
import { usersApi } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [data, setData] = useState({ email: "", password: "", nombre: "", headline: "" });
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [cityError, setCityError] = useState("");
  const [confirm, setConfirm] = useState("");
  const [acceptsTerms, setAcceptsTerms] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof data) => (value: string) => setData((old) => ({ ...old, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!selectedCity) {
      setCityError("Seleccioná una ciudad de la lista.");
      return;
    }
    if (data.password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    if (!acceptsTerms) {
      setError("Aceptá los Términos y Condiciones para crear la cuenta.");
      return;
    }
    setBusy(true);
    try {
      await usersApi.create({ ...data, ciudad: selectedCity, acepta_terminos: acceptsTerms });
      router.push("/login?registro=ok");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo crear la cuenta.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="register-page"><header className="auth-header"><Link href="/login" aria-label="Atanes"><Image src="/assets/atanes_logo.svg" alt="Atanes" width={2037} height={772} className="wordmark"/></Link><nav><Link href="/login" className="active-auth">Iniciar sesión</Link></nav></header><section className="register-content"><h1>Unite a tu comunidad profesional</h1><form onSubmit={submit} className="register-form"><label>Nombre completo<input required maxLength={100} value={data.nombre} onChange={(e) => set("nombre")(e.target.value)}/></label><label>Email<input type="email" required maxLength={100} value={data.email} onChange={(e) => set("email")(e.target.value)}/></label><label>Titular profesional<input required maxLength={200} value={data.headline} onChange={(e) => set("headline")(e.target.value)}/></label><CityAutocomplete selectedCity={selectedCity} onSelect={(city) => { setSelectedCity(city); if (city) setCityError(""); }} validationError={cityError} disabled={busy}/><label>Contraseña (8 caracteres como mínimo)<input type="password" required minLength={8} value={data.password} onChange={(e) => set("password")(e.target.value)}/></label><label>Confirmar contraseña<input type="password" required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)}/></label>{error && <p className="auth-error" role="alert">{error}</p>}<label className="register-terms"><input type="checkbox" checked={acceptsTerms} onChange={(e) => setAcceptsTerms(e.target.checked)} disabled={busy}/><span>Acepto los <Link href="/terminos">Términos y Condiciones</Link></span></label><button className="auth-primary" disabled={busy || !acceptsTerms}>{busy ? "Creando cuenta..." : "Aceptar y unirse"}</button><p>Al crear la cuenta, confirmás que aceptás los <Link href="/terminos">Términos y Condiciones</Link>.</p></form><p>¿Ya estás en Atanes? <Link href="/login">Iniciar sesión</Link></p></section></main>;
}
