"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { companiesApi, type CompanyTeamMember } from "@/lib/api";
import {
  companyRoleLabels,
  filterCompanyMembers,
} from "@/lib/company-members";

export function CompanyTeam({ companyId }: { companyId: number }) {
  const [members, setMembers] = useState<CompanyTeamMember[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;

    companiesApi
      .getMembers(companyId)
      .then((loaded) => {
        if (active) setMembers(loaded);
      })
      .catch((loadError) => {
        if (active) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "No se pudo cargar el equipo.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [companyId, retry]);

  const visibleMembers = useMemo(
    () => filterCompanyMembers(members, query),
    [members, query],
  );

  return (
    <section className="card profile-section company-team">
      <div className="company-team-heading">
        <div>
          <h2>Equipo</h2>
          <p>Personas que forman parte de esta empresa.</p>
        </div>
        {!loading && !error && <span>{members.length} {members.length === 1 ? "miembro" : "miembros"}</span>}
      </div>

      {!loading && !error && members.length > 0 && (
        <label className="company-team-search">
          <span className="sr-only">Buscar miembros por nombre</span>
          <Icon name="search" width={21}/>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar miembros por nombre"
          />
        </label>
      )}

      {loading ? (
        <p className="company-team-state" role="status">Cargando miembros...</p>
      ) : error ? (
        <div className="company-team-state">
          <p className="inline-error">{error}</p>
          <button
            className="text-button"
            onClick={() => {
              setLoading(true);
              setError("");
              setRetry((value) => value + 1);
            }}
          >
            Reintentar
          </button>
        </div>
      ) : members.length === 0 ? (
        <p className="company-team-state">Esta empresa todavía no tiene miembros.</p>
      ) : visibleMembers.length === 0 ? (
        <p className="company-team-state">No se encontraron miembros.</p>
      ) : (
        <div className="company-team-list">
          {visibleMembers.map((member) => (
            <Link
              href={`/perfil/${member.usuario_id}`}
              className="company-team-member"
              key={member.usuario_id}
            >
              <Avatar name={member.nombre} src={member.foto_perfil_url} size={56}/>
              <span className="company-team-member-copy">
                <strong>{member.nombre}</strong>
                {member.headline && <small>{member.headline}</small>}
              </span>
              <span className="company-team-role">{companyRoleLabels[member.rol]}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
