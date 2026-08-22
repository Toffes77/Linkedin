"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { notificationsApi, type Notification } from "@/lib/api";
import { formatDate } from "@/lib/format";

function notificationHref(notification: Notification) {
  if (notification.tipo === "POSTULACION_ESTADO") return "/empleos#applications";
  return notification.oferta_id ? `/empleos/${notification.oferta_id}` : "/empleos";
}

export default function NotificationsPage() {
  const router = useRouter(); const [notifications, setNotifications] = useState<Notification[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { notificationsApi.list().then(setNotifications).catch((e) => setError(e instanceof Error ? e.message : "No se pudieron cargar las notificaciones")).finally(() => setLoading(false)); }, []);
  async function markRead(notification: Notification) { if (notification.leida) return; try { const updated = await notificationsApi.markRead(notification.id); setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item)); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo actualizar la notificación"); } }
  async function openNotification(event: React.MouseEvent<HTMLAnchorElement>, notification: Notification) { event.preventDefault(); await markRead(notification); router.push(notificationHref(notification)); }
  return <AppShell><main className="app-background"><div className="single-column"><section className="card notifications-list"><h1>Notificaciones</h1>{error && <p className="inline-error">{error}</p>}{loading ? <div className="skeleton result-skeleton"/> : notifications.length ? notifications.map((notification) => <Link className={`notification-item ${notification.leida ? "" : "unread"}`} href={notificationHref(notification)} onClick={(event) => openNotification(event, notification)} key={notification.id}><span className="notification-dot" aria-hidden="true"/><div><strong>{notification.mensaje}</strong><small>{formatDate(notification.fecha)}</small></div></Link>) : <div className="empty-state">No tenés notificaciones por ahora.</div>}</section></div></main></AppShell>;
}
