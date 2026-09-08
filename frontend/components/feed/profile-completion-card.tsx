"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@/lib/api";
import {
  getProfileCompletionCardState,
  getProfileCompletion,
  markProfileCompletionActionStarted,
  markProfileCompletionShown,
  PROFILE_COMPLETION_TOTAL,
} from "@/lib/profile-completion";

type CardState = "checking" | "incomplete" | "completed" | "hidden";

const COMPLETION_MESSAGE_DURATION_MS = 3_000;

export function ProfileCompletionCard({ user }: { user: User }) {
  const [state, setState] = useState<CardState>("checking");
  const completion = getProfileCompletion(user);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      try {
        const nextState = getProfileCompletionCardState(user, window.localStorage);
        if (nextState === "completed") {
          markProfileCompletionShown(user.id, window.localStorage);
          setState("completed");
        } else setState(nextState);
      } catch {
        setState(completion.hasPhoto ? "hidden" : "incomplete");
      }
    });
    return () => { active = false; };
  }, [completion.hasPhoto, completion.completed, user]);

  useEffect(() => {
    if (state !== "completed") return;
    const timeout = window.setTimeout(() => setState("hidden"), COMPLETION_MESSAGE_DURATION_MS);
    return () => window.clearTimeout(timeout);
  }, [state]);

  if (state === "checking" || state === "hidden") return null;

  if (state === "completed") return <section className="card onboarding profile-completion-card" aria-live="polite">
    <div><h1>Perfil completado</h1><span>{PROFILE_COMPLETION_TOTAL}/{PROFILE_COMPLETION_TOTAL} completado</span></div>
    <div className="progress"><i style={{ width: "100%" }}/></div>
    <div className="onboarding-visual"><strong>Tu perfil ya está listo</strong><p>Tu foto de perfil se agregó correctamente.</p></div>
  </section>;

  return <section className="card onboarding profile-completion-card">
    <div><h1>Completar perfil</h1><span>{completion.completed}/{PROFILE_COMPLETION_TOTAL} completado</span></div>
    <div className="progress"><i style={{ width: `${(completion.completed / PROFILE_COMPLETION_TOTAL) * 100}%` }}/></div>
    <div className="onboarding-visual"><strong>Agregar foto de perfil</strong><p>Una foto ayuda a que tu red te reconozca.</p><Link href="/perfil/editar?tab=photo" className="primary-button" onClick={() => {
      try { markProfileCompletionActionStarted(user.id, window.localStorage); } catch {
        // La carga de la foto sigue disponible aunque el navegador no permita almacenamiento local.
      }
    }}>Agregar foto de perfil</Link></div>
  </section>;
}
