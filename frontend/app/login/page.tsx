"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { SessionLoader } from "@/components/session-loader";

export default function LoginPage() {
  const router = useRouter(); const { user, loading, login } = useAuth(); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false);
  useEffect(() => { if (!loading && user) router.replace("/feed"); }, [loading, router, user]);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setSubmitting(true); try { await login(email, password); router.replace("/feed"); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo iniciar sesión."); } finally { setSubmitting(false); } }
  if (loading || user) return <SessionLoader/>;
  return <main className="auth-page"><header className="auth-header"><Link href="/login" aria-label="Atanes"><Image src="/assets/atanes_logo.svg" alt="Atanes" width={2037} height={772} className="wordmark" preload/></Link><nav><Link href="/registro" className="join-link">Unirse ahora</Link><Link href="/login" className="active-auth" aria-current="page">Iniciar sesión</Link></nav></header>
    <div className="auth-hero"><section className="auth-copy"><h1>¡Te damos la bienvenida a<br/>tu comunidad profesional!</h1><form onSubmit={submit} className="login-form"><label>Email<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><label>Contraseña<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button disabled={submitting} className="auth-primary">{submitting ? "Iniciando sesión..." : "Iniciar sesión"}</button></form><p className="terms">Al hacer clic en «Iniciar sesión», aceptas las Condiciones de uso, la Política de privacidad y la Política de cookies de Atanes.</p><p className="auth-switch">¿Estás empezando a usar Atanes? <Link href="/registro">Únete ahora</Link></p></section>
      <div className="auth-illustration"><Image src="/assets/imagen_derecha_login.png" alt="Profesional trabajando con su notebook" width={610} height={503} priority/></div></div>
  </main>;
}
