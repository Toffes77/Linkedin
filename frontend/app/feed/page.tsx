"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ProfileCard } from "@/components/feed/profile-card";
import { Composer } from "@/components/feed/composer";
import { PostCard } from "@/components/feed/post-card";
import { postsApi, usersApi, type Post, type User } from "@/lib/api";

export default function FeedPage() {
  const { user } = useAuth(); const [posts, setPosts] = useState<Post[]>([]); const [authors, setAuthors] = useState<Record<number, User>>({}); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!user) return; let active = true; postsApi.feed().then(async (items) => { if (!active) return; setPosts(items); const ids = [...new Set(items.map((post) => post.autor_id))]; const loaded = await Promise.all(ids.map((id) => usersApi.get(id).catch(() => null))); if (active) setAuthors(Object.fromEntries(loaded.filter((author): author is User => author !== null).map((author) => [author.id, author]))); }).catch((e) => active && setError(e instanceof Error ? e.message : "No se pudo cargar el feed")).finally(() => active && setLoading(false)); return () => { active = false; }; }, [user]);
  if (!user) return null;
  return <AppShell><main className="app-background"><div className="feed-grid"><ProfileCard user={user}/><div className="feed-center">
    <section className="card onboarding"><div><h1>Ponte en marcha en Atanes</h1><span>1/3 completado</span></div><div className="progress"><i/></div><div className="onboarding-visual"><strong>Mostrá tu experiencia profesional</strong><p>Completá tu perfil para que tu red conozca tu recorrido.</p><Link href="/perfil/editar" className="primary-button">Actualizar perfil</Link></div></section>
    <Composer user={user} onCreated={(post) => setPosts((old) => [post, ...old])}/>
    {error && <section className="card empty-state">{error}</section>}{loading ? <><div className="card skeleton post-skeleton"/><div className="card skeleton post-skeleton"/></> : posts.length ? posts.map((post) => <PostCard key={post.id} post={post} author={authors[post.autor_id] ?? (post.autor_id === user.id ? user : undefined)} currentUser={user} onDelete={(id) => setPosts((old) => old.filter((p) => p.id !== id))} onUpdate={(updated) => setPosts((old) => old.map((p) => p.id === updated.id ? updated : p))}/>) : <section className="card empty-state"><strong>Tu feed está tranquilo</strong><p>Conectate con personas para ver sus publicaciones acá.</p><Link href="/mi-red" className="secondary-button">Ampliar mi red</Link></section>}
  </div><aside className="feed-right card"><h2>Añadir a tu feed</h2><p>Descubrí profesionales mediante la búsqueda y ampliá tu red.</p><Link href="/buscar?q=desarrollador">Buscar personas →</Link><hr/><h3>Tu comunidad profesional</h3><p>Creá publicaciones y compartí novedades con tus contactos.</p></aside></div></main></AppShell>;
}
