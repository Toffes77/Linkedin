import Link from "next/link";
import type { User } from "@/lib/api";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { getMostRecentExperience } from "@/lib/experience-recency";

export function ProfileCard({ user }: { user: User }) {
  const mostRecentExperience = getMostRecentExperience(user.experiencias);
  return <aside className="feed-left">
    <section className="card profile-card">
      <div className="profile-cover" />
      <Link href={`/perfil/${user.id}`}><Avatar name={user.nombre} src={user.foto_perfil_url} size={88} className="profile-card-avatar"/></Link>
      <div className="profile-card-body"><Link href={`/perfil/${user.id}`} className="profile-name">{user.nombre}</Link><p>{user.headline}</p><small>{user.ciudad}</small></div>
      <Link href="/perfil/editar?tab=experience#experiencias" className="profile-company"><Icon name="briefcase" width={18}/><span><strong>Experiencias</strong><small>{mostRecentExperience?.puesto ?? "Añadí tu experiencia"}</small></span></Link>
    </section>
  </aside>;
}
