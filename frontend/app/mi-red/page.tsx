"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { PersonCard } from "@/components/network/person-card";
import { usersApi, type User } from "@/lib/api";

export default function NetworkPage() {
  const { user } = useAuth(); const [people, setPeople] = useState<User[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!user) return; usersApi.suggestions(user.id).then(setPeople).catch((e) => setError(e instanceof Error ? e.message : "No se pudieron cargar sugerencias")).finally(() => setLoading(false)); }, [user]);
  return <AppShell><main className="app-background"><div className="network-layout"><aside><section className="card network-summary"><h1>Resumen de la red</h1><div><span><strong>—</strong>Invitaciones enviadas</span><span><strong>—</strong>Contactos</span><span><strong>—</strong>Siguiendo</span></div><p>Los totales no están disponibles en la API.</p></section><footer className="network-footer">Acerca de　 Accesibilidad　 Centro de ayuda<br/>Privacidad y condiciones<br/><strong>LinkedIn</strong> Corporation © 2026</footer></aside><div className="network-main"><section className="card invitation-bar"><h2>Invitaciones recibidas</h2><span>No existe listado disponible</span></section><section className="card suggestions"><header><h2>Gente que podrías conocer</h2></header>{error && <div className="empty-state">{error}</div>}{loading ? <div className="people-grid"><div className="person-card skeleton"/><div className="person-card skeleton"/><div className="person-card skeleton"/></div> : people.length ? <div className="people-grid">{people.map((person) => <PersonCard key={person.id} person={person}/>)}</div> : <div className="empty-state"><strong>No hay sugerencias nuevas</strong><p>Cuando tengas conexiones, aparecerán contactos de segundo grado acá.</p></div>}</section></div></div></main></AppShell>;
}
