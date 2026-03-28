"""
Exceções do Velox Framework
"""


class VeloxException(Exception):
    """Exceção base do Velox Framework"""
    def __init__(self, message, status_code=500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class HTTPException(VeloxException):
    """Exceção HTTP base"""
    def __init__(self, message, status_code=500):
        super().__init__(message, status_code)


class NotFoundError(HTTPException):
    """Erro 404 - Página não encontrada"""
    def __init__(self, message="Página não encontrada"):
        super().__init__(message, 404)


class ForbiddenError(HTTPException):
    """Erro 403 - Acesso proibido"""
    def __init__(self, message="Acesso proibido"):
        super().__init__(message, 403)


class UnauthorizedError(HTTPException):
    """Erro 401 - Não autorizado"""
    def __init__(self, message="Não autorizado"):
        super().__init__(message, 401)


class BadRequestError(HTTPException):
    """Erro 400 - Requisição inválida"""
    def __init__(self, message="Requisição inválida"):
        super().__init__(message, 400)


class ValidationError(HTTPException):
    """Erro de validação"""
    def __init__(self, message="Erro de validação"):
        super().__init__(message, 422)


class DatabaseError(VeloxException):
    """Erro de banco de dados"""
    def __init__(self, message="Erro no banco de dados"):
        super().__init__(message, 500)


class TemplateError(VeloxException):
    """Erro de template"""
    def __init__(self, message="Erro ao renderizar template"):
        super().__init__(message, 500)


class ConfigurationError(VeloxException):
    """Erro de configuração"""
    def __init__(self, message="Erro de configuração"):
        super().__init__(message, 500)


# Decorador para tratamento de exceções
def error_handler(app):
    """Decorator para registrar handlers de erro global"""
    def decorator(func):
        app._error_handler = func
        return func
    return decorator
