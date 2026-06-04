import logging

import structlog

from core.config import settings

SENSITIVE_KEYS = frozenset(
    {"password", "token", "secret", "authorization", "cookie", "csrf_token"}
)


def _filter_sensitive(
    logger: object, method: str, event_dict: dict[str, object]
) -> dict[str, object]:
    return {
        k: "***" if k.lower() in SENSITIVE_KEYS else v for k, v in event_dict.items()
    }


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _filter_sensitive,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
