"use client";

import Link from "next/link";
import { useState } from "react";
import { connectionsApi, type User } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";

export function PersonCard({ person }: { person: User }) {
  const { user } = useAuth(); const [state, setState] = useState<"idle" | "busy" | "sent">("idle"); const [error, setError] = useState("");
  async function connect() { if (!user) return; setState("busy"); setError(""); try { await connectionsApi.create(user.id, person.id); setState("sent"); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo conectar"); setState("idle"); } }
  return <article className="person-card"><div className="person-cover"/><Link href={`/perfil/${person.id}`}><Avatar name={person.nombre} src={person.foto_perfil_url} size={112}/><strong>{person.nombre}</strong></Link><p>{person.headline}</p><small>{person.ciudad}</small><button onClick={connect} disabled={state !== "idle"} className="secondary-button">{state === "busy" ? "Enviando..." : state === "sent" ? "Pendiente" : "+ Conectar"}</button>{error && <span className="inline-error">{error}</span>}</article>;
}
