"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";
import { PostCard } from "@/components/feed/post-card";
import {
  companiesApi,
  connectionsApi,
  followsApi,
  postsApi,
  usersApi,
  type Company,
  type ConnectionStatus,
  type Post,
  type User,
} from "@/lib/api";
import { formatMonth } from "@/lib/format";

const connectionLabels = {
  SIN_CONEXION: "Conectar",
  PENDIENTE_ENVIADA: "Pendiente",
  PENDIENTE_RECIBIDA: "Aceptar conexión",
  CONECTADO: "Conectado",
  RECHAZADA: "Solicitud rechazada",
} as const;

export default function ProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user: current, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState<User | null>(null);
  const [companies, setCompanies] = useState<Record<number, Company>>({});
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [following, setFollowing] = useState(false);
  const [followBusy, setFollowBusy] = useState(false);

  useEffect(() => {
    if (authLoading || !current) return;
    const userId = Number(id);
    let active = true;

    usersApi
      .get(userId)
      .then(async (loaded) => {
        const ids = [...new Set(loaded.experiencias.map((experience) => experience.empresa_id))];
        const [list, profilePosts, followStatus, relationStatus] = await Promise.all([
          Promise.all(ids.map((companyId) => companiesApi.get(companyId).catch(() => null))),
          postsApi.byAuthor(userId),
          current.id !== userId ? followsApi.status(userId) : Promise.resolve(null),
          current.id !== userId ? connectionsApi.status(userId) : Promise.resolve(null),
        ]);
        if (!active) return;
        setError("");
        setProfile(loaded);
        setPosts(profilePosts);
        setFollowing(followStatus?.siguiendo ?? false);
        setConnectionStatus(relationStatus);
        setCompanies(
          Object.fromEntries(
            list
              .filter((company): company is Company => company !== null)
              .map((company) => [company.id, company]),
          ),
        );
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "No se pudo cargar el perfil");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [id, current, authLoading]);

  async function handleConnection() {
    if (!current || !profile || !connectionStatus) return;
    if (connectionStatus.estado !== "SIN_CONEXION" && connectionStatus.estado !== "PENDIENTE_RECIBIDA") return;

    setConnectionBusy(true);
    setError("");
    try {
      if (connectionStatus.estado === "SIN_CONEXION") {
        await connectionsApi.create(current.id, profile.id);
        setConnectionStatus({ estado: "PENDIENTE_ENVIADA", usuario_a: current.id, usuario_b: profile.id });
      } else if (connectionStatus.usuario_a !== null && connectionStatus.usuario_b !== null) {
        await connectionsApi.respond(connectionStatus.usuario_a, connectionStatus.usuario_b, "aceptada");
        setConnectionStatus({ ...connectionStatus, estado: "CONECTADO" });
      }
    } catch (connectionError) {
      setError(connectionError instanceof Error ? connectionError.message : "No se pudo actualizar la conexión");
    } finally {
      setConnectionBusy(false);
    }
  }

  async function toggleFollow() {
    if (!profile) return;
    setFollowBusy(true);
    setError("");
    try {
      if (following) await followsApi.unfollow(profile.id);
      else await followsApi.follow(profile.id);
      setFollowing((value) => !value);
    } catch (followError) {
      setError(followError instanceof Error ? followError.message : "No se pudo actualizar el seguimiento");
    } finally {
      setFollowBusy(false);
    }
  }

  const canActOnConnection = connectionStatus?.estado === "SIN_CONEXION" || connectionStatus?.estado === "PENDIENTE_RECIBIDA";
  const connectionLabel = connectionBusy ? "Actualizando..." : connectionStatus ? connectionLabels[connectionStatus.estado] : "Cargando...";

  return (
    <AppShell>
      <main className="app-background">
        <div className="profile-layout">
          {loading ? <div className="card skeleton profile-skeleton"/> : error && !profile ? <div className="card empty-state">{error}</div> : profile && <>
            <section className="card profile-hero">
              <div className="large-cover"/>
              <Avatar name={profile.nombre} src={profile.foto_perfil_url} size={150} className="large-avatar"/>
              <div className="profile-info">
                <h1>{profile.nombre}</h1>
                <p>{profile.headline}</p>
                <span>{profile.ciudad}</span>
                <div>
                  {current?.id === profile.id ? <Link href="/perfil/editar" className="primary-button">Editar perfil</Link> : <>
                    <button onClick={handleConnection} disabled={connectionBusy || !canActOnConnection} className="primary-button">{connectionLabel}</button>
                    <button onClick={toggleFollow} disabled={followBusy} className="secondary-button">{followBusy ? "Actualizando..." : following ? "Siguiendo" : "Seguir"}</button>
                  </>}
                </div>
              </div>
            </section>
            <section className="card profile-section"><h2>Acerca de</h2><p>{profile.headline}</p></section>
            <section className="card profile-section">
              <h2>Experiencia</h2>
              {profile.experiencias.length ? profile.experiencias.map((experience) => <article className="experience-row" key={experience.id}><span className="company-placeholder">{companies[experience.empresa_id]?.nombre.slice(0, 1) ?? "E"}</span><div><h3>{experience.puesto}</h3>{companies[experience.empresa_id] ? <Link href={`/empresas/${experience.empresa_id}`}>{companies[experience.empresa_id].nombre}</Link> : <span>Empresa #{experience.empresa_id}</span>}<p>{formatMonth(experience.desde)} – {formatMonth(experience.hasta)}</p></div></article>) : <p className="muted">Todavía no agregó experiencias.</p>}
            </section>
            <section className="profile-posts">
              <h2>Publicaciones</h2>
              {posts.length ? posts.map((post) => <PostCard key={post.id} post={post} author={profile} currentUser={current!} onDelete={(postId) => setPosts((items) => items.filter((item) => item.id !== postId))} onUpdate={(updated) => setPosts((items) => items.map((item) => item.id === updated.id ? updated : item))}/>) : <section className="card profile-section"><p className="muted">{current?.id === profile.id ? "Todavía no realizaste publicaciones." : "Este usuario todavía no realizó publicaciones."}</p></section>}
            </section>
            {error && <p className="inline-error">{error}</p>}
          </>}
        </div>
      </main>
    </AppShell>
  );
}
