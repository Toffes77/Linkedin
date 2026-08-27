"use client";

import { FormEvent, useEffect, useState } from "react";
import { boardApi, type Promotion } from "@/lib/api";

export function PromotionForm({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (promotion: Promotion) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) { if (event.key === "Escape") onClose(); }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmedTitle = title.trim();
    const trimmedDescription = description.trim();
    if (!trimmedTitle || !trimmedDescription) {
      setError("Completá el título y la descripción.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      onCreated(await boardApi.createPromotion({ titulo: trimmedTitle, descripcion: trimmedDescription }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo crear la promoción.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="board-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="board-modal card" role="dialog" aria-modal="true" aria-labelledby="create-promotion-title">
      <header><div><span className="board-kicker">Tablón</span><h2 id="create-promotion-title">Crear promoción</h2></div><button type="button" className="board-close" onClick={onClose} aria-label="Cerrar">×</button></header>
      <form onSubmit={submit} className="board-form">
        <label>Título profesional<input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} placeholder="Ej. Desarrollador Backend" required /></label>
        <label>Descripción<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={3000} rows={7} placeholder="Contá qué hacés y qué oportunidad estás buscando." required /></label>
        <small>{description.length}/3000</small>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <footer><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button type="submit" className="primary-button" disabled={saving}>{saving ? "Publicando..." : "Publicar promoción"}</button></footer>
      </form>
    </section>
  </div>;
}
