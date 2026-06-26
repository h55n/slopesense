"""
SlopeSense backend package.

Configures structured logging (structlog) for production observability.
"""

import logging
import logging.handlers
import os
from pathlib import Path

import structlog


def configure_logging():
    """Initialize structured logging for the backend.

    In production (ENVIRONMENT=production), logs are JSON-formatted
    and written to both stderr and a rotating file under logs/.
    In development, standard console formatting is used.
    """
    env = os.getenv("ENVIRONMENT", "development")
    is_prod = env == "production"

    log_level = os.getenv("LOG_LEVEL", "INFO" if is_prod else "DEBUG").upper()
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_prod:
        handlers = [
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                log_dir / "slopesense.log",
                maxBytes=100_000_000,
                backupCount=10,
            ),
        ]
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        handlers = [logging.StreamHandler()]
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
    )

    # Quiet noisy third-party loggers in production
    if is_prod:
        for logger_name in ("uvicorn.access", "httpx", "urllib3", "botocore", "s3fs"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)



configure_logging()
