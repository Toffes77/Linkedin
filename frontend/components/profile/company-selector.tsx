"use client";

import { useEffect, useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { ApiError, companiesApi, type Company } from "@/lib/api";

export function CompanySelector({
  selected,
  onSelect,
}: {
  selected: Company | null;
  onSelect: (company: Company | null) => void;
}) {
  const [query, setQuery] = useState(selected?.nombre ?? "");
  const [results, setResults] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2 || selected?.nombre === query) return;

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      companiesApi.search(term, controller.signal)
        .then((companies) => {
          setResults(companies);
          setError("");
        })
        .catch((reason) => {
          if (controller.signal.aborted) return;
          setResults([]);
          setError(reason instanceof ApiError ? reason.message : "No se pudieron buscar empresas.");
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, selected?.nombre]);

  function changeQuery(value: string) {
    setQuery(value);
    setResults([]);
    setError("");
    setLoading(value.trim().length >= 2);
    if (selected) onSelect(null);
  }

  function choose(company: Company) {
    setQuery(company.nombre);
    setResults([]);
    setLoading(false);
    setError("");
    onSelect(company);
  }

  return <div className="company-selector">
    <label htmlFor="experience-company">Empresa</label>
    <input
      id="experience-company"
      value={query}
      onChange={(event) => changeQuery(event.target.value)}
      placeholder="Buscar empresa por nombre"
      autoComplete="off"
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={results.length > 0}
      aria-controls="experience-company-results"
      required
    />
    {loading ? <span className="company-selector-status">Buscando empresas...</span> : null}
    {error ? <span className="inline-error" role="alert">{error}</span> : null}
    {!loading && query.trim().length >= 2 && !selected && results.length === 0 && !error ? <span className="company-selector-status">No se encontraron empresas.</span> : null}
    {results.length > 0 ? <div id="experience-company-results" className="company-selector-results" role="listbox">
      {results.map((company) => <button type="button" role="option" aria-selected={selected?.id === company.id} key={company.id} onClick={() => choose(company)}>
        <Avatar name={company.nombre} src={company.foto_perfil_url} size={38}/>
        <span><strong>{company.nombre}</strong><small>{company.industria ?? "Empresa de Atanes"}</small></span>
      </button>)}
    </div> : null}
    {selected ? <span className="company-selector-selection">Empresa seleccionada: <strong>{selected.nombre}</strong></span> : null}
  </div>;
}
