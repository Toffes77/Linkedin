"use client";

import { ChangeEvent, RefObject, useRef, useState } from "react";
import {
  MESSAGE_BACKGROUND_OPTIONS,
  MESSAGE_FONT_OPTIONS,
  type MessageFontId,
  type MessagePreferences,
} from "@/components/messages/message-preferences-storage";

const ACCEPTED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_IMAGE_SIZE = 3 * 1024 * 1024;

export function MessagePreferencesMenu({
  menuRef,
  preferences,
  hasCustomImage,
  onBackgroundColorChange,
  onImageSelected,
  onResetBackground,
  onFontChange,
  onResetPreferences,
}: {
  menuRef: RefObject<HTMLDivElement | null>;
  preferences: MessagePreferences;
  hasCustomImage: boolean;
  onBackgroundColorChange: (color: string) => Promise<void>;
  onImageSelected: (image: File) => Promise<void>;
  onResetBackground: () => Promise<void>;
  onFontChange: (font: MessageFontId) => void;
  onResetPreferences: () => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [savingImage, setSavingImage] = useState(false);

  async function selectImage(event: ChangeEvent<HTMLInputElement>) {
    const image = event.target.files?.[0];
    event.target.value = "";
    if (!image) return;
    if (!ACCEPTED_IMAGE_TYPES.has(image.type)) {
      setImageError("Elegí una imagen PNG, JPG o WEBP.");
      return;
    }
    if (image.size > MAX_IMAGE_SIZE) {
      setImageError("La imagen debe pesar como máximo 3 MB.");
      return;
    }

    setSavingImage(true);
    setImageError(null);
    try {
      await onImageSelected(image);
    } catch {
      setImageError("No se pudo guardar la imagen en este navegador.");
    } finally {
      setSavingImage(false);
    }
  }

  async function chooseColor(color: string) {
    setImageError(null);
    await onBackgroundColorChange(color);
  }

  return <div className="message-preferences-menu" ref={menuRef} role="dialog" aria-labelledby="message-preferences-title">
    <div className="message-preferences-heading">
      <h2 id="message-preferences-title">Preferencias de mensajes</h2>
      <span>Solo cambian la apariencia de tus chats.</span>
    </div>

    <section className="message-preferences-section" aria-labelledby="message-background-heading">
      <h3 id="message-background-heading">Fondo del chat</h3>
      <div className="message-color-options">
        {MESSAGE_BACKGROUND_OPTIONS.map((option) => <button
          key={option.value}
          type="button"
          className={preferences.backgroundColor === option.value && !hasCustomImage ? "selected" : ""}
          style={{ backgroundColor: option.value }}
          onClick={() => void chooseColor(option.value)}
          aria-label={`Usar fondo ${option.label}`}
          aria-pressed={preferences.backgroundColor === option.value && !hasCustomImage}
          title={option.label}
        />)}
      </div>
      <input ref={inputRef} className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={selectImage}/>
      <div className="message-background-actions">
        <button type="button" className="message-preference-button" disabled={savingImage} onClick={() => inputRef.current?.click()}>
          {savingImage ? "Guardando imagen..." : hasCustomImage ? "Cambiar imagen" : "Elegir imagen"}
        </button>
        <button type="button" className="message-preference-link" onClick={() => void onResetBackground()}>Restablecer fondo</button>
      </div>
      {hasCustomImage ? <span className="message-image-status">Imagen personalizada activa</span> : null}
      {imageError ? <p className="message-preference-error" role="status">{imageError}</p> : null}
    </section>

    <section className="message-preferences-section" aria-labelledby="message-font-heading">
      <label id="message-font-heading" htmlFor="message-font-select">Fuente de mensajes</label>
      <select
        id="message-font-select"
        value={preferences.font}
        style={{ fontFamily: MESSAGE_FONT_OPTIONS.find((option) => option.value === preferences.font)?.family }}
        onChange={(event) => onFontChange(event.target.value as MessageFontId)}
      >
        {MESSAGE_FONT_OPTIONS.map((option) => <option key={option.value} value={option.value} style={{ fontFamily: option.family }}>{option.label}</option>)}
      </select>
    </section>

    <button type="button" className="message-reset-preferences" onClick={() => void onResetPreferences()}>Restablecer preferencias</button>
  </div>;
}
