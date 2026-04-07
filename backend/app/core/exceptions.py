class AppException(Exception):
    """Base exception for application-level errors.

    Caught by the global exception handler in main.py and converted
    to the standard JSON error response format.
    """

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with ID {resource_id} not found",
            status_code=404,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(code="CONFLICT", message=message, status_code=409)


class ValidationError(AppException):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422)
        self.field = field
