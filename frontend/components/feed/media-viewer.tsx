"use client";

import { useEffect } from "react";
import Image from "next/image";
import { mediaUrl, type PostMedia } from "@/lib/api";
import { carouselIndex } from "@/lib/post-media";

export function MediaViewer({ items, index, onIndexChange, onClose }: { items: PostMedia[]; index: number; onIndexChange: (index: number) => void; onClose: () => void }) {
  const current = items[index];

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft") onIndexChange(carouselIndex(index, -1, items.length));
      if (event.key === "ArrowRight") onIndexChange(carouselIndex(index, 1, items.length));
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [index, items.length, onClose, onIndexChange]);

  if (!current) return null;
  const source = mediaUrl(current.ruta) ?? "";
  return <div className="media-viewer-backdrop" role="dialog" aria-modal="true" aria-label="Visor de multimedia" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="media-viewer">
      <button type="button" className="media-viewer-close" onClick={onClose} aria-label="Cerrar visor">×</button>
      <div className="media-viewer-stage">
        {current.tipo === "IMAGEN" ? <Image unoptimized fill sizes="100vw" src={source} alt={`Imagen ${index + 1} de la publicación`}/> : <video key={current.id} src={source} controls autoPlay playsInline>Tu navegador no puede reproducir este video.</video>}
      </div>
      <div className="media-viewer-controls">
        <button type="button" onClick={() => onIndexChange(carouselIndex(index, -1, items.length))} aria-label="Multimedia anterior" disabled={items.length < 2}>←</button>
        <strong aria-live="polite">{index + 1} / {items.length}</strong>
        <button type="button" onClick={() => onIndexChange(carouselIndex(index, 1, items.length))} aria-label="Multimedia siguiente" disabled={items.length < 2}>→</button>
      </div>
    </div>
  </div>;
}
