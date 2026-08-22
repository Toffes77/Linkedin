import Image from "next/image";
import Link from "next/link";
import { mediaUrl, type Company } from "@/lib/api";

export function CompanyCard({ company }: { company: Company }) {
  const logo = mediaUrl(company.foto_perfil_url);
  return <Link href={`/empresas/${company.id}`} className="company-list-card">
    <div className="company-card-logo">{logo ? <Image unoptimized src={logo} alt={`Logo de ${company.nombre}`} width={72} height={72}/> : <span>{company.nombre.trim().slice(0, 1).toUpperCase()}</span>}</div>
    <div className="company-card-copy"><h3>{company.nombre}</h3>{company.industria && <p>{company.industria}</p>}{company.sitio_web && <span>{company.sitio_web.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span>}</div>
    <span className="company-card-arrow" aria-hidden="true">›</span>
  </Link>;
}
