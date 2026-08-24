import type { CompanyRole, CompanyTeamMember } from "@/lib/api";

const rolePriority: Record<CompanyRole, number> = {
  OWNER: 0,
  RECRUITER: 1,
  COLLABORATOR: 2,
};

const nameCollator = new Intl.Collator("es", { sensitivity: "base" });

export const companyRoleLabels: Record<CompanyRole, string> = {
  OWNER: "Owner",
  RECRUITER: "Recruiter",
  COLLABORATOR: "Colaborador",
};

function normalizeName(value: string) {
  return value
    .trim()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("es");
}

export function filterCompanyMembers(
  members: CompanyTeamMember[],
  query: string,
) {
  const normalizedQuery = normalizeName(query);

  return [...members]
    .filter(
      (member) =>
        !normalizedQuery || normalizeName(member.nombre).includes(normalizedQuery),
    )
    .sort(
      (first, second) =>
        rolePriority[first.rol] - rolePriority[second.rol] ||
        nameCollator.compare(first.nombre, second.nombre) ||
        first.usuario_id - second.usuario_id,
    );
}
