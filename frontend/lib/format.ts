export function formatDate(value: string | null | undefined) {
  if (!value) return "Actualidad";
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export function formatMonth(value: string | null | undefined) {
  if (!value) return "Actualidad";
  return new Intl.DateTimeFormat("es-AR", { month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export function formatRelativeDate(value: string) {
  const date = new Date(value);
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (elapsedSeconds < 60) return "ahora";
  const minutes = Math.floor(elapsedSeconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} d`;
  return formatDate(value);
}
