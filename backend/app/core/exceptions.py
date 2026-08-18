class QWIException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(QWIException):
    def __init__(self, resource: str = "Recurso"):
        # Aceita tanto o nome do recurso ("Weekly") quanto uma mensagem já
        # pronta ("Weekly não encontrado"): se já tem espaço, usa como está —
        # evita o "... não encontrado not found" duplicado (QA-038).
        text = resource.strip()
        message = text if " " in text else f"{text} não encontrado"
        super().__init__(message, status_code=404)


class UnauthorizedError(QWIException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(QWIException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ValidationError(QWIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)
