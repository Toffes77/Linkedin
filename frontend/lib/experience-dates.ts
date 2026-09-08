export type ExperienceDates = {
  desde: string;
  hasta: string;
};

export function getLocalDateForInput(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function validateExperienceDates(
  { desde, hasta }: ExperienceDates,
  today = getLocalDateForInput(),
): string | null {
  if (desde && desde > today) return "La fecha de inicio no puede ser posterior a hoy.";
  if (hasta && hasta > today) return "La fecha de finalización no puede ser posterior a hoy.";
  if (desde && hasta && hasta < desde) {
    return "La fecha de finalización no puede ser anterior a la fecha de inicio.";
  }
  return null;
}
