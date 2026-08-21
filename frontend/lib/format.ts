export function formatDate(value: string | null | undefined) {
  if (!value) return "Actualidad";
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export function formatMonth(value: string | null | undefined) {
  if (!value) return "Actualidad";
  return new Intl.DateTimeFormat("es-AR", { month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}
