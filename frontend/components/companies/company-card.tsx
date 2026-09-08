import Link from "next/link";
import type { Company } from "@/lib/api";
import { CompanyLogo } from "@/components/companies/company-logo";

export function CompanyCard({ company }: { company: Company }) {
  return <Link href={`/empresas/${company.id}`} className="company-list-card">
    <CompanyLogo name={company.nombre} src={company.foto_perfil_url} className="company-card-logo"/>
    <div className="company-card-copy"><h3>{company.nombre}</h3>{company.industria && <p>{company.industria}</p>}{company.sitio_web && <span>{company.sitio_web.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span>}</div>
    <span className="company-card-arrow" aria-hidden="true">›</span>
  </Link>;
}
