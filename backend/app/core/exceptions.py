class DomainError(Exception):
    code = "domain_error"
    status_code = 500
    def __init__(self, detail: str = "Error de dominio"):
        self.detail = detail
        super().__init__(detail)
class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404
class ValidationError(DomainError):
    code = "validation_error"
    status_code = 400
class InfrastructureError(DomainError):
    code = "infrastructure_error"
    status_code = 503