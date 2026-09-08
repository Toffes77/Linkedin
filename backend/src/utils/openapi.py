from typing import Any

from src.schemas.error_schema import ErrorResponseSchema


_ERROR_DESCRIPTIONS = {
    400: "La solicitud es inválida según una regla de negocio.",
    401: "Falta la autenticación o el token no es válido.",
    403: "La identidad está autenticada, pero no tiene permiso para la operación.",
    404: "El recurso solicitado no existe o no es visible para la identidad actual.",
    409: "La operación entra en conflicto con el estado actual del recurso.",
}


def error_responses(*status_codes: int, validation: bool = True) -> dict[int, dict[str, Any]]:
    """Construye respuestas OpenAPI para errores de dominio y validación."""

    responses: dict[int, dict[str, Any]] = {
        status_code: {
            "model": ErrorResponseSchema,
            "description": _ERROR_DESCRIPTIONS[status_code],
        }
        for status_code in status_codes
    }
    if validation:
        responses[422] = {
            "description": (
                "Los parámetros de ruta/query, el formulario o el body no cumplen "
                "el schema Pydantic."
            )
        }
    return responses
