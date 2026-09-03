"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ProfileCard } from "@/components/feed/profile-card";
import { Composer } from "@/components/feed/composer";
import { PostCard } from "@/components/feed/post-card";
import {
  appendUniqueById,
  canRequestFeedCursor,
  excludeItemById,
  failedFeedContinuation,
  releaseFailedFeedCursor,
  successfulFeedContinuation,
  uniqueById,
} from "@/lib/feed-pagination";
import { postsApi, type FeedPost, type Post, type User } from "@/lib/api";

const FEED_PAGE_SIZE = 10;

function enrichCreatedPost(post: Post, author: User): FeedPost {
  return {
    ...post,
    autor: {
      id: author.id,
      nombre: author.nombre,
      headline: author.headline,
      foto_perfil_url: author.foto_perfil_url,
    },
    reacciones: { like: 0, celebrar: 0, apoyar: 0, interesante: 0 },
    mi_reaccion: null,
    cantidad_comentarios: 0,
  };
}

export default function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ publicacion?: string | string[] }>;
}) {
  const rawSharedPostId = use(searchParams).publicacion;
  const parsedSharedPostId = Number(Array.isArray(rawSharedPostId) ? rawSharedPostId[0] : rawSharedPostId);
  const requestedSharedPostId = Number.isInteger(parsedSharedPostId) && parsedSharedPostId > 0 ? parsedSharedPostId : null;
  const { user } = useAuth();
  const [sharedPostId] = useState(requestedSharedPostId);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [sharedPost, setSharedPost] = useState<FeedPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const [loadMoreError, setLoadMoreError] = useState("");
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingPageRef = useRef(false);
  const hasMoreRef = useRef(true);
  const nextCursorRef = useRef<string | null>(null);
  const requestedCursorsRef = useRef(new Set<string>());
  const requestRef = useRef<AbortController | null>(null);
  const activeUserRef = useRef<number | null>(null);

  useEffect(() => {
    if (!user) return;
    const currentUser = user;

    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    activeUserRef.current = currentUser.id;
    loadingPageRef.current = true;
    hasMoreRef.current = true;
    nextCursorRef.current = null;
    requestedCursorsRef.current = new Set<string>();
    async function loadFirstPage() {
      try {
        const [feedPage, requestedPost] = await Promise.all([
          postsApi.feed({
            pageSize: FEED_PAGE_SIZE,
            excludePostId: sharedPostId,
            signal: controller.signal,
          }),
          sharedPostId
            ? postsApi.get(sharedPostId, controller.signal).catch(() => null)
            : Promise.resolve(null),
        ]);
        if (controller.signal.aborted || activeUserRef.current !== currentUser.id) return;
        const items = feedPage.items;
        const firstPage = excludeItemById(uniqueById(items), requestedPost?.id);
        setSharedPost(requestedPost);
        setError("");
        setLoadMoreError("");
        setLoadingMore(false);
        const continuation = successfulFeedContinuation(feedPage.next_cursor, feedPage.has_more);
        nextCursorRef.current = continuation.cursor;
        hasMoreRef.current = continuation.hasMore;
        setHasMore(continuation.hasMore);
        setPosts(firstPage);
        if (sharedPostId) window.history.replaceState(window.history.state, "", "/feed");
      } catch (reason) {
        if (controller.signal.aborted) return;
        setPosts([]);
        setError(reason instanceof Error ? reason.message : "No se pudo cargar el feed");
      } finally {
        if (!controller.signal.aborted && activeUserRef.current === currentUser.id) {
          loadingPageRef.current = false;
          setLoading(false);
        }
      }
    }

    void loadFirstPage();
    return () => {
      controller.abort();
      requestRef.current?.abort();
      if (requestRef.current === controller) requestRef.current = null;
    };
  }, [sharedPostId, user]);

  const loadNextPage = useCallback(async () => {
    if (!user) return;

    const cursor = nextCursorRef.current;
    if (!cursor || !canRequestFeedCursor(
      cursor,
      loadingPageRef.current,
      hasMoreRef.current,
      requestedCursorsRef.current,
    )) return;

    requestedCursorsRef.current.add(cursor);
    loadingPageRef.current = true;
    setLoadingMore(true);
    setLoadMoreError("");
    const controller = new AbortController();
    requestRef.current = controller;

    try {
      const feedPage = await postsApi.feed({
        cursor,
        pageSize: FEED_PAGE_SIZE,
        excludePostId: sharedPostId,
        signal: controller.signal,
      });
      if (controller.signal.aborted || activeUserRef.current !== user.id) return;
      const items = feedPage.items;
      const continuation = successfulFeedContinuation(feedPage.next_cursor, feedPage.has_more);
      nextCursorRef.current = continuation.cursor;
      hasMoreRef.current = continuation.hasMore;
      setHasMore(continuation.hasMore);
      const incoming = excludeItemById(uniqueById(items), sharedPostId);
      setPosts((current) => appendUniqueById(current, incoming));
    } catch (reason) {
      if (controller.signal.aborted) return;
      releaseFailedFeedCursor(requestedCursorsRef.current, cursor);
      const continuation = failedFeedContinuation(
        cursor,
        hasMoreRef.current,
        reason instanceof Error ? reason.message : "No se pudo cargar más publicaciones",
      );
      nextCursorRef.current = continuation.cursor;
      setLoadMoreError(continuation.loadError);
    } finally {
      if (!controller.signal.aborted && activeUserRef.current === user.id) {
        loadingPageRef.current = false;
        setLoadingMore(false);
      }
    }
  }, [sharedPostId, user]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || loading || loadingMore || loadMoreError || !hasMore) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadNextPage();
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadMoreError, loadNextPage, loading, loadingMore, posts.length]);

  if (!user) return null;
  return <AppShell><main className="app-background"><div className="feed-grid"><ProfileCard user={user}/><div className="feed-center">
    <section className="card onboarding"><div><h1>Ponte en marcha en Atanes</h1><span>1/3 completado</span></div><div className="progress"><i/></div><div className="onboarding-visual"><strong>Mostrá tu experiencia profesional</strong><p>Completá tu perfil para que tu red conozca tu recorrido.</p><Link href="/perfil/editar?tab=experience#experiencias" className="primary-button">Agregar experiencia</Link></div></section>
    <Composer user={user} onCreated={(post) => setPosts((current) => [enrichCreatedPost(post, user), ...current.filter((item) => item.id !== post.id && item.id !== sharedPost?.id)])}/>
    {!loading && sharedPost ? <PostCard key={`shared-${sharedPost.id}`} post={sharedPost} highlighted currentUser={user} onDelete={() => setSharedPost(null)} onUpdate={setSharedPost}/> : null}
    {loading ? <><div className="card skeleton post-skeleton"/><div className="card skeleton post-skeleton"/></> : posts.length ? posts.map((post) => <PostCard key={post.id} post={post} currentUser={user} onDelete={(id) => setPosts((current) => current.filter((post) => post.id !== id))} onUpdate={(updated) => setPosts((current) => current.map((post) => post.id === updated.id ? updated : post))}/>) : !sharedPost && !error && <section className="card empty-state"><strong>Tu feed está tranquilo</strong><p>Todavía no hay publicaciones para mostrar.</p></section>}
    {error && <section className="card empty-state feed-pagination-error" role="alert">{error}</section>}
    {loadMoreError && <section className="card empty-state feed-pagination-error" role="alert"><p>{loadMoreError}</p><button type="button" className="secondary-button" disabled={loadingMore} onClick={() => void loadNextPage()}>Reintentar</button></section>}
    {loadingMore && <div className="feed-page-loader" role="status"><span className="session-spinner"/><span>Cargando más publicaciones...</span></div>}
    {!loading && !loadMoreError && hasMore && posts.length > 0 && <div ref={sentinelRef} className="feed-sentinel" aria-hidden="true"/>}
  </div><aside className="feed-right card"><h2>Añadir a tu feed</h2><p>Descubrí profesionales mediante la búsqueda y ampliá tu red.</p><Link href="/buscar?q=desarrollador">Buscar personas →</Link><hr/><h3>Tu comunidad profesional</h3><p>Creá publicaciones y compartí novedades con tus contactos.</p></aside></div></main></AppShell>;
}
