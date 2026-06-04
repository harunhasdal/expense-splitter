import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = structlog.get_logger()


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    if isinstance(exc, OperationalError):
        logger.error("database_error", correlation_id=correlation_id, exc_info=exc)
        return JSONResponse(
            {"error": "Service temporarily unavailable", "correlation_id": correlation_id},
            status_code=503,
            headers={"Retry-After": "30"},
        )

    logger.error("unhandled_exception", correlation_id=correlation_id, exc_info=exc)
    return JSONResponse(
        {"error": "Internal server error", "correlation_id": correlation_id},
        status_code=500,
    )
