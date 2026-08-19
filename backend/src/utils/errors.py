class AppError(Exception):
    status_code: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    message = "Bad request"


class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"


class UnauthorizedError(AppError):
    status_code = 401
    message = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    message = "Forbidden"


class ConflictError(AppError):
    status_code = 409
    message = "Conflict"
