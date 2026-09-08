from datetime import date


def validar_fechas_experiencia(
    desde: date | None,
    hasta: date | None,
    *,
    hoy: date | None = None,
) -> None:
    """Valida fechas civiles de una experiencia sin convertirlas a timestamps."""

    fecha_actual = hoy or date.today()
    if desde is not None and desde > fecha_actual:
        raise ValueError("La fecha de inicio no puede ser posterior a hoy.")
    if hasta is not None and hasta > fecha_actual:
        raise ValueError("La fecha de finalización no puede ser posterior a hoy.")
    if desde is not None and hasta is not None and hasta < desde:
        raise ValueError(
            "La fecha de finalización no puede ser anterior a la fecha de inicio."
        )
