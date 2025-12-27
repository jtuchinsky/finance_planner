class FinanceTrackerException(Exception):
    """Base exception for finance tracker"""

    pass


class UnauthorizedException(FinanceTrackerException):
    """Raised when JWT validation fails"""

    pass


class NotFoundException(FinanceTrackerException):
    """Raised when resource not found"""

    pass


class ForbiddenException(FinanceTrackerException):
    """Raised when user tries to access another user's data"""

    pass


class ValidationException(FinanceTrackerException):
    """Raised for business logic validation errors"""

    pass