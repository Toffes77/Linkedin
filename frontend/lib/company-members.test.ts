import assert from "node:assert/strict";
import test from "node:test";

import type { CompanyTeamMember } from "./api.ts";
import {
  companyRoleLabels,
  filterCompanyMembers,
} from "./company-members.ts";

const members: CompanyTeamMember[] = [
  { usuario_id: 6, nombre: "Pedro López", headline: "Backend", foto_perfil_url: null, rol: "COLLABORATOR" },
  { usuario_id: 3, nombre: "Santino Conca", headline: "RRHH", foto_perfil_url: null, rol: "RECRUITER" },
  { usuario_id: 2, nombre: "Luca De Lauro", headline: "Owner", foto_perfil_url: null, rol: "OWNER" },
  { usuario_id: 5, nombre: "Lucas Fernández", headline: "Frontend", foto_perfil_url: null, rol: "COLLABORATOR" },
  { usuario_id: 1, nombre: "Juan Cruz Maletti", headline: "Owner", foto_perfil_url: null, rol: "OWNER" },
  { usuario_id: 4, nombre: "Benjamin Gomez", headline: "Recruiter", foto_perfil_url: null, rol: "RECRUITER" },
];

test("an empty query returns every member ordered by role and name", () => {
  assert.deepEqual(
    filterCompanyMembers(members, "").map((member) => member.usuario_id),
    [1, 2, 4, 3, 5, 6],
  );
});

test("search is partial, trimmed, case-insensitive and accent-insensitive", () => {
  assert.deepEqual(
    filterCompanyMembers(members, "  LUC  ").map((member) => member.nombre),
    ["Luca De Lauro", "Lucas Fernández"],
  );
  assert.deepEqual(
    filterCompanyMembers(members, "lopez").map((member) => member.nombre),
    ["Pedro López"],
  );
});

test("clearing the query immediately restores the complete ordered list", () => {
  assert.equal(filterCompanyMembers(members, "juan").length, 1);
  assert.equal(filterCompanyMembers(members, "   ").length, members.length);
  assert.equal(members[0].usuario_id, 6, "the original API list is not mutated");
});

test("roles use readable labels", () => {
  assert.deepEqual(companyRoleLabels, {
    OWNER: "Owner",
    RECRUITER: "Recruiter",
    COLLABORATOR: "Colaborador",
  });
});
