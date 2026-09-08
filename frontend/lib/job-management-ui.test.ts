import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const jobPage = readFileSync(
  new URL("../app/empleos/[id]/page.tsx", import.meta.url),
  "utf8",
);
const api = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const newCompanyPage = readFileSync(
  new URL("../app/empresas/nueva/page.tsx", import.meta.url),
  "utf8",
);
const editCompanyPage = readFileSync(
  new URL("../app/empresas/[id]/editar/page.tsx", import.meta.url),
  "utf8",
);
const jobsPage = readFileSync(
  new URL("../app/empleos/page.tsx", import.meta.url),
  "utf8",
);
const companyPage = readFileSync(
  new URL("../app/empresas/[id]/page.tsx", import.meta.url),
  "utf8",
);
const companyLogo = readFileSync(
  new URL("../components/companies/company-logo.tsx", import.meta.url),
  "utf8",
);

test("las postulaciones usan identidad real y el Avatar compartido", () => {
  assert.match(api, /ApplicationApplicant = \{ id: number; nombre: string; foto_perfil_url: string \| null \}/);
  assert.match(jobPage, /<Avatar name=\{application\.postulante\.nombre\} src=\{application\.postulante\.foto_perfil_url\} size=\{42\}\/>/);
  assert.match(jobPage, /\{application\.postulante\.nombre\}/);
  assert.doesNotMatch(jobPage, /Usuario \{application\.usuario_id\}/);
});

test("la interfaz de administración no expone texto técnico", () => {
  assert.match(jobPage, /Solo los OWNER y RECRUITER de la empresa pueden acceder a esta sección\./);
  assert.doesNotMatch(jobPage, /FastAPI/);
});

test("alta y edición de empresa muestran el label de industria actualizado", () => {
  assert.match(newCompanyPage, /Industria \(descripción\)/);
  assert.match(editCompanyPage, /Industria \(descripción\)/);
});

test("las ofertas muestran el logo real de la empresa sin requests por oferta", () => {
  assert.match(jobsPage, /<CompanyLogo/);
  assert.match(jobsPage, /companiesApi\.getBatch\(companyIds\)/);
  assert.doesNotMatch(jobsPage, /companiesApi\.get\(/);
  assert.match(jobPage, /<CompanyLogo name=\{company\?\.nombre/);
  assert.match(companyPage, /<CompanyLogo name=\{company\.nombre\}/);
  assert.match(companyLogo, /mediaUrl\(src\)/);
  assert.match(companyLogo, /name\.trim\(\)\.slice\(0, 1\)\.toUpperCase\(\)/);
});

test("el listado de empresa limita la descripción y mantiene el detalle completo", () => {
  assert.match(companyPage, /className="job-row-description">\{item\.descripcion\}/);
  assert.match(jobPage, /className="job-description">\{job\.descripcion\}/);
  assert.match(
    readFileSync(new URL("../app/globals.css", import.meta.url), "utf8"),
    /\.job-row-description[\s\S]*-webkit-line-clamp:3/,
  );
});

test("Despublicar se renderiza como botón con estado ocupado", () => {
  assert.match(companyPage, /className="secondary-button job-toggle-button"/);
  assert.match(companyPage, /disabled=\{jobActionBusyId !== null\}/);
  assert.match(companyPage, /jobActionBusyId === item\.id \? "Guardando\.\.\."/);
});
