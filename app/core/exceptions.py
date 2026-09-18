"""Custom exceptions for controlled error handling."""
from fastapi import HTTPException, status


class GridWiseError(Exception):
    """Base exception for GridWise."""


class LLMError(GridWiseError):
    """Raised when LLM call fails or returns invalid output."""


class LLMRateLimited(GridWiseError):
    """Raised when LLM provider rate-limits us. Temporary."""


class GuardrailError(GridWiseError):
    """Raised when LLM output fails deterministic validation."""


class OptimizerError(GridWiseError):
    """Raised when the optimizer cannot find a feasible solution."""


class InvalidRequestError(GridWiseError):
    """Raised when the request is structurally or semantically invalid."""


def to_http_exception(exc: GridWiseError) -> HTTPException:
    """Map internal exceptions to HTTP responses."""
    if isinstance(exc, InvalidRequestError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if isinstance(exc, GuardrailError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, LLMRateLimited):
        # 503 tells the judge: "temporary, retry later"
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider rate limit reached. Please retry shortly.",
            headers={"Retry-After": "5"},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal processing error. Please try again.",
    )