"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { notificationsApi } from "@/lib/api";

const nav = [
  { href: "/feed", label: "Inicio", icon: "home" as const },
  { href: "/mi-red", label: "Mi red", icon: "network" as const },
  { href: "/empleos", label: "Empleos", icon: "jobs" as const },
  { href: "/tablon", label: "Tablón", icon: "board" as const },
];

export function Header() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  useEffect(() => { if (!user) return; notificationsApi.unreadCount().then(({ cantidad }) => setUnread(cantidad)).catch(() => setUnread(0)); }, [user, pathname]);
  function search(event: FormEvent) { event.preventDefault(); if (query.trim()) router.push(`/buscar?q=${encodeURIComponent(query.trim())}`); }
  async function signOut() { await logout(); router.replace("/login"); }
  return <header className="site-header">
    <div className="header-inner">
      <Link href="/feed" className="mini-logo" aria-label="Atanes inicio"><Image src="/assets/atanes_logo_chico.svg" alt="" width={1254} height={1254} className="mini-logo-image" preload/></Link>
      <form onSubmit={search} className="header-search">
        <Icon name="search" width={21} />
        <label className="sr-only" htmlFor="global-search">Buscar personas</label>
        <input id="global-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar" />
      </form>
      <nav className="main-nav" aria-label="Navegación principal">
        {nav.map((item) => <Link key={item.href} href={item.href} className={pathname.startsWith(item.href) ? "active" : ""}><Icon name={item.icon} /><span>{item.label}</span></Link>)}
        <Link href="/empresas" className={pathname === "/empresas" || pathname.startsWith("/empresas/") ? "active" : ""}><Icon name="company"/><span>Empresas</span></Link>
        <Link href="/notificaciones" className={pathname === "/notificaciones" ? "active notifications-nav" : "notifications-nav"}><Icon name="bell"/>{unread > 0 && <b className="notification-badge">{unread > 99 ? "99+" : unread}</b>}<span>Notificaciones</span></Link>
        <div className="profile-menu-wrap">
          <button className="nav-profile" onClick={() => setOpen(!open)} aria-expanded={open}>
            {user && <Avatar name={user.nombre} src={user.foto_perfil_url} size={25}/>}<span>Yo ▾</span>
          </button>
          {open && <div className="profile-menu">
            {user && <Link href={`/perfil/${user.id}`} onClick={() => setOpen(false)}>Ver perfil</Link>}
            <Link href="/perfil/editar" onClick={() => setOpen(false)}>Ajustes del perfil</Link>
            <button onClick={signOut}>Cerrar sesión</button>
          </div>}
        </div>
        <Link href="/empresas/nueva" className="business-nav"><Icon name="business"/><span>Para negocios</span></Link>
      </nav>
    </div>
  </header>;
}
