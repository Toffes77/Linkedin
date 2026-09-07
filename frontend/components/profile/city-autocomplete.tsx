"use client";

import {
  KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { ApiError, locationsApi, type CitySuggestion } from "@/lib/api";
import {
  citySelectionAfterInput,
  nextCityOptionIndex,
} from "@/lib/city-autocomplete-state";

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;

export function CityAutocomplete({
  selectedCity,
  onSelect,
  validationError = "",
  disabled = false,
}: {
  selectedCity: string | null;
  onSelect: (city: string | null) => void;
  validationError?: string;
  disabled?: boolean;
}) {
  const generatedId = useId().replace(/:/g, "");
  const inputId = `city-${generatedId}`;
  const listId = `${inputId}-results`;
  const validationId = `${inputId}-validation`;
  const containerRef = useRef<HTMLDivElement>(null);
  const requestSequence = useRef(0);
  const [query, setQuery] = useState(selectedCity ?? "");
  const [results, setResults] = useState<CitySuggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const term = query.trim();
    const sequence = ++requestSequence.current;
    if (term.length < MIN_QUERY_LENGTH || selectedCity === query) {
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setLoading(true);
      setOpen(true);
      locationsApi.searchCities(term, 10, controller.signal)
        .then((cities) => {
          if (controller.signal.aborted || sequence !== requestSequence.current) return;
          setResults(cities);
          setActiveIndex(-1);
          setSearched(true);
          setError("");
        })
        .catch((reason) => {
          if (controller.signal.aborted || sequence !== requestSequence.current) return;
          setResults([]);
          setSearched(true);
          setError(reason instanceof ApiError ? reason.message : "No se pudieron cargar las ciudades.");
        })
        .finally(() => {
          if (!controller.signal.aborted && sequence === requestSequence.current) {
            setLoading(false);
          }
        });
    }, DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, selectedCity]);

  useEffect(() => {
    function closeOnOutsideClick(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, []);

  function changeQuery(value: string) {
    setQuery(value);
    setResults([]);
    setActiveIndex(-1);
    setOpen(value.trim().length >= MIN_QUERY_LENGTH);
    setLoading(false);
    setSearched(false);
    setError("");
    onSelect(citySelectionAfterInput(selectedCity, value));
  }

  function choose(city: CitySuggestion) {
    setQuery(city.nombre);
    setResults([]);
    setActiveIndex(-1);
    setOpen(false);
    setLoading(false);
    setSearched(false);
    setError("");
    onSelect(city.nombre);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp" && event.key !== "Enter") return;
    if (event.key === "Enter") {
      if (open && activeIndex >= 0 && results[activeIndex]) {
        event.preventDefault();
        choose(results[activeIndex]);
      }
      return;
    }
    event.preventDefault();
    setOpen(true);
    setActiveIndex((current) => nextCityOptionIndex(
      current,
      event.key === "ArrowDown" ? "next" : "previous",
      results.length,
    ));
  }

  const showDropdown = open
    && query.trim().length >= MIN_QUERY_LENGTH
    && (loading || searched || Boolean(error) || results.length > 0);
  const activeOptionId = activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined;

  return <div className="company-selector city-selector" ref={containerRef}>
    <label htmlFor={inputId}>Ciudad</label>
    <input
      id={inputId}
      value={query}
      onChange={(event) => changeQuery(event.target.value)}
      onFocus={() => {
        if (!selectedCity && query.trim().length >= MIN_QUERY_LENGTH) setOpen(true);
      }}
      onKeyDown={handleKeyDown}
      placeholder="Escribí tu ciudad..."
      autoComplete="off"
      maxLength={100}
      disabled={disabled}
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={showDropdown}
      aria-controls={listId}
      aria-activedescendant={activeOptionId}
      aria-invalid={Boolean(validationError)}
      aria-describedby={validationError ? validationId : undefined}
      aria-required="true"
    />
    {showDropdown ? <div id={listId} className="company-selector-results city-selector-results" role="listbox">
      {loading ? <span className="company-selector-status">Buscando...</span> : null}
      {!loading && error ? <span className="inline-error" role="alert">{error}</span> : null}
      {!loading && !error && searched && results.length === 0 ? <span className="company-selector-status">No se encontraron ciudades.</span> : null}
      {!loading && !error ? results.map((city, index) => <button
        id={`${listId}-${index}`}
        type="button"
        role="option"
        aria-selected={activeIndex === index}
        className={activeIndex === index ? "active" : ""}
        key={city.nombre}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => choose(city)}
      >
        <span><strong>{city.nombre}</strong></span>
      </button>) : null}
    </div> : null}
    {validationError ? <span id={validationId} className="inline-error city-validation-error" role="alert">{validationError}</span> : null}
  </div>;
}
