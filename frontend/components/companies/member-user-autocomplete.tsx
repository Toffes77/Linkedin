"use client";

import {
  KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { Avatar } from "@/components/common/avatar";
import { ApiError, companiesApi, type User } from "@/lib/api";
import {
  memberUserSelectionAfterInput,
  nextMemberUserOptionIndex,
} from "@/lib/member-user-autocomplete-state";

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;
const RESULT_LIMIT = 10;

export function MemberUserAutocomplete({
  companyId,
  selectedUser,
  onSelect,
}: {
  companyId: number;
  selectedUser: User | null;
  onSelect: (user: User | null) => void;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const requestSequence = useRef(0);
  const listboxId = useId();
  const inputId = useId();
  const [query, setQuery] = useState(selectedUser?.nombre ?? "");
  const [results, setResults] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [error, setError] = useState("");

  useEffect(() => {
    const handleOutsideClick = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", handleOutsideClick);
    return () => document.removeEventListener("pointerdown", handleOutsideClick);
  }, []);

  useEffect(() => {
    const term = query.trim();
    if (term.length < MIN_QUERY_LENGTH || selectedUser?.nombre === query) {
      return;
    }

    const controller = new AbortController();
    const sequence = ++requestSequence.current;
    const timeout = window.setTimeout(() => {
      companiesApi
        .searchMemberCandidates(companyId, term, {
          limit: RESULT_LIMIT,
          signal: controller.signal,
        })
        .then((page) => {
          if (sequence !== requestSequence.current) return;
          setResults(page.items);
          setSearched(true);
          setActiveIndex(-1);
          setError("");
          setOpen(true);
        })
        .catch((reason) => {
          if (controller.signal.aborted || sequence !== requestSequence.current) {
            return;
          }
          setResults([]);
          setSearched(true);
          setError(
            reason instanceof ApiError
              ? reason.message
              : "No se pudieron buscar usuarios.",
          );
          setOpen(true);
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
  }, [companyId, query, selectedUser?.nombre]);

  function changeQuery(value: string) {
    requestSequence.current += 1;
    setQuery(value);
    setResults([]);
    setSearched(false);
    setActiveIndex(-1);
    setError("");
    const shouldSearch = value.trim().length >= MIN_QUERY_LENGTH;
    setLoading(shouldSearch);
    setOpen(shouldSearch);
    const nextSelection = memberUserSelectionAfterInput(selectedUser, value);
    if (nextSelection !== selectedUser) onSelect(nextSelection);
  }

  function choose(user: User) {
    requestSequence.current += 1;
    setQuery(user.nombre);
    setResults([]);
    setSearched(false);
    setLoading(false);
    setOpen(false);
    setActiveIndex(-1);
    setError("");
    onSelect(user);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) =>
        nextMemberUserOptionIndex(
          current,
          event.key === "ArrowDown" ? "next" : "previous",
          results.length,
        ),
      );
      return;
    }
    if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      choose(results[activeIndex]);
    }
  }

  const showPanel =
    open &&
    !selectedUser &&
    query.trim().length >= MIN_QUERY_LENGTH &&
    (loading || searched || Boolean(error));

  return (
    <div className="company-selector member-user-selector" ref={rootRef}>
      <label htmlFor={inputId}>Persona</label>
      <input
        id={inputId}
        value={query}
        onChange={(event) => changeQuery(event.target.value)}
        onFocus={() => {
          if (!selectedUser && query.trim().length >= MIN_QUERY_LENGTH) {
            setOpen(true);
          }
        }}
        onKeyDown={handleKeyDown}
        placeholder="Escribir nombre..."
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showPanel}
        aria-controls={listboxId}
        aria-activedescendant={
          activeIndex >= 0 ? `${listboxId}-${results[activeIndex]?.id}` : undefined
        }
      />

      {showPanel ? (
        <div
          id={listboxId}
          className="company-selector-results member-user-results"
          role="listbox"
        >
          {loading ? (
            <span className="company-selector-status" role="status">
              Buscando usuarios...
            </span>
          ) : error ? (
            <span className="inline-error" role="alert">{error}</span>
          ) : results.length === 0 ? (
            <span className="company-selector-status">
              No se encontraron usuarios.
            </span>
          ) : (
            results.map((user, index) => (
              <button
                id={`${listboxId}-${user.id}`}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                className={index === activeIndex ? "active" : ""}
                key={user.id}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(user)}
              >
                <Avatar name={user.nombre} src={user.foto_perfil_url} size={42}/>
                <span>
                  <strong>{user.nombre}</strong>
                  <small>{user.headline || "Sin titular profesional"}</small>
                  {user.ciudad ? <small>{user.ciudad}</small> : null}
                </span>
              </button>
            ))
          )}
        </div>
      ) : null}

      {selectedUser ? (
        <div className="member-user-selection" aria-live="polite">
          <Avatar
            name={selectedUser.nombre}
            src={selectedUser.foto_perfil_url}
            size={42}
          />
          <span>
            <strong>{selectedUser.nombre}</strong>
            <small>{selectedUser.headline || "Sin titular profesional"}</small>
            {selectedUser.ciudad ? <small>{selectedUser.ciudad}</small> : null}
          </span>
        </div>
      ) : null}
    </div>
  );
}
