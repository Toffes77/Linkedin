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
  canRequestFeedPage,
  excludeItemById,
  feedHasMore,
  uniqueById,
} from "@/lib/feed-pagination";
import { postsApi, usersApi, type Post, type User } from "@/lib/api";

const FEED_PAGE_SIZE = 10;

export default function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ publicacion?: string | string[] }>;
}) {
  const rawSharedPostId = use(searchParams).publicacion;
  const parsedSharedPostId = Number(Array.isArray(rawSharedPostId) ? rawSharedPostId[0] : rawSharedPostId);
  const sharedPostId = Number.isInteger(parsedSharedPostId) && parsedSharedPostId > 0 ? parsedSharedPostId : null;
  const { user } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [sharedPost, setSharedPost] = useState<Post | null>(null);
  const [authors, setAuthors] = useState<Record<number, User>>({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingPageRef = useRef(false);
  const hasMoreRef = useRef(true);
  const nextPageRef = useRef(1);
  const loadedPagesRef = useRef(new Set<number>());
  const authorIdsRef = useRef(new Set<number>());
  const requestRef = useRef<AbortController | null>(null);
  const activeUserRef = useRef<number | null>(null);

  const loadAuthors = useCallback(async (items: Post[], signal: AbortSignal) => {
    const ids = [...new Set(items.map((post) => post.autor_id))].filter(
      (id) => !authorIdsRef.current.has(id),
    );
    ids.forEach((id) => authorIdsRef.current.add(id));
    if (!ids.length) return;

    const loaded = await Promise.all(
      ids.map((id) => usersApi.get(id).catch(() => null)),
    );
    if (signal.aborted) return;
    const validAuthors = loaded.filter((author): author is User => author !== null);
    setAuthors((current) => ({
      ...current,
      ...Object.fromEntries(validAuthors.map((author) => [author.id, author])),
    }));
  }, []);

  useEffect(() => {
    if (!user) return;
    const currentUser = user;

    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    activeUserRef.current = currentUser.id;
    loadingPageRef.current = true;
    hasMoreRef.current = true;
    nextPageRef.current = 1;
    loadedPagesRef.current = new Set<number>();
    authorIdsRef.current = new Set<number>([currentUser.id]);

    async function loadFirstPage() {
      try {
        const [items, requestedPost] = await Promise.all([
          postsApi.feed(1, FEED_PAGE_SIZE, controller.signal),
          sharedPostId
            ? postsApi.get(sharedPostId, controller.signal).catch(() => null)
            : Promise.resolve(null),
        ]);
        if (controller.signal.aborted || activeUserRef.current !== currentUser.id) return;
        const firstPage = excludeItemById(uniqueById(items), requestedPost?.id);
        setAuthors({ [currentUser.id]: currentUser });
        setSharedPost(requestedPost);
        setError("");
        setLoadingMore(false);
        loadedPagesRef.current.add(1);
        nextPageRef.current = 2;
        const canLoadMore = feedHasMore(items.length, FEED_PAGE_SIZE);
        hasMoreRef.current = canLoadMore;
        setHasMore(canLoadMore);
        setPosts(firstPage);
        await loadAuthors(requestedPost ? [requestedPost, ...firstPage] : firstPage, controller.signal);
        if (sharedPostId) window.history.replaceState(window.history.state, "", "/feed");
      } catch (reason) {
        if (controller.signal.aborted) return;
        setPosts([]);
        hasMoreRef.current = false;
        setHasMore(false);
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
  }, [loadAuthors, sharedPostId, user]);

  const loadNextPage = useCallback(async () => {
    if (!user) return;

    const page = nextPageRef.current;
    if (!canRequestFeedPage(
      page,
      loadingPageRef.current,
      hasMoreRef.current,
      loadedPagesRef.current,
    )) return;

    loadingPageRef.current = true;
    setLoadingMore(true);
    setError("");
    const controller = new AbortController();
    requestRef.current = controller;

    try {
      const items = await postsApi.feed(page, FEED_PAGE_SIZE, controller.signal);
      if (controller.signal.aborted || activeUserRef.current !== user.id) return;
      loadedPagesRef.current.add(page);
      nextPageRef.current = page + 1;
      const canLoadMore = feedHasMore(items.length, FEED_PAGE_SIZE);
      hasMoreRef.current = canLoadMore;
      setHasMore(canLoadMore);
      const incoming = excludeItemById(uniqueById(items), sharedPost?.id);
      setPosts((current) => appendUniqueById(current, incoming));
      await loadAuthors(incoming, controller.signal);
    } catch (reason) {
      if (controller.signal.aborted) return;
      hasMoreRef.current = false;
      setHasMore(false);
      setError(reason instanceof Error ? reason.message : "No se pudo cargar más publicaciones");
    } finally {
      if (!controller.signal.aborted && activeUserRef.current === user.id) {
        loadingPageRef.current = false;
        setLoadingMore(false);
      }
    }
  }, [loadAuthors, sharedPost, user]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || loading || loadingMore || !hasMore) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadNextPage();
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadNextPage, loading, loadingMore, posts.length]);

  if (!user) return null;
  return <AppShell><main className="app-background"><div className="feed-grid"><ProfileCard user={user}/><div className="feed-center">
    <section className="card onboarding"><div><h1>Ponte en marcha en Atanes</h1><span>1/3 completado</span></div><div className="progress"><i/></div><div className="onboarding-visual"><strong>Mostrá tu experiencia profesional</strong><p>Completá tu perfil para que tu red conozca tu recorrido.</p><Link href="/perfil/editar?tab=experience#experiencias" className="primary-button">Agregar experiencia</Link></div></section>
    <Composer user={user} onCreated={(post) => setPosts((current) => [post, ...current.filter((item) => item.id !== post.id && item.id !== sharedPost?.id)])}/>
    {!loading && sharedPost ? <PostCard key={`shared-${sharedPost.id}`} post={sharedPost} highlighted author={authors[sharedPost.autor_id] ?? (sharedPost.autor_id === user.id ? user : undefined)} currentUser={user} onDelete={() => setSharedPost(null)} onUpdate={setSharedPost}/> : null}
    {loading ? <><div className="card skeleton post-skeleton"/><div className="card skeleton post-skeleton"/></> : posts.length ? posts.map((post) => <PostCard key={post.id} post={post} author={authors[post.autor_id] ?? (post.autor_id === user.id ? user : undefined)} currentUser={user} onDelete={(id) => setPosts((current) => current.filter((post) => post.id !== id))} onUpdate={(updated) => setPosts((current) => current.map((post) => post.id === updated.id ? updated : post))}/>) : !sharedPost && !error && <section className="card empty-state"><strong>Tu feed está tranquilo</strong><p>Todavía no hay publicaciones para mostrar.</p></section>}
    {error && <section className="card empty-state feed-pagination-error" role="alert">{error}</section>}
    {loadingMore && <div className="feed-page-loader" role="status"><span className="session-spinner"/><span>Cargando más publicaciones...</span></div>}
    {!loading && hasMore && posts.length > 0 && <div ref={sentinelRef} className="feed-sentinel" aria-hidden="true"/>}
  </div><aside className="feed-right card"><h2>Añadir a tu feed</h2><p>Descubrí profesionales mediante la búsqueda y ampliá tu red.</p><Link href="/buscar?q=desarrollador">Buscar personas →</Link><hr/><h3>Tu comunidad profesional</h3><p>Creá publicaciones y compartí novedades con tus contactos.</p></aside></div></main></AppShell>;
}
