"""OpenAI-style error helpers."""
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class BflProxyError(Exception):
    """Raised to produce an OpenAI-style error response."""

    def __init__(
        self,
        message: str,
        type: str = "bfl_api_error",
        code: Optional[str] = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.type = type
        self.code = code
        self.status_code = status_code


def error_response(
    message: str,
    type: str = "bfl_api_error",
    code: Optional[str] = None,
    status_code: int = 500,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": type,
                "code": code,
            }
        },
    )


async def bfl_proxy_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, BflProxyError):
        return error_response(exc.message, exc.type, exc.code, exc.status_code)
    return error_response(str(exc) or "Internal error", "internal_error", "internal_error", 500)