from __future__ import annotations

from logging.config import dictConfig

import structlog


def _console_renderer() -> structlog.dev.ConsoleRenderer:
    return structlog.dev.ConsoleRenderer(colors=False)


def configure_logging(level: str) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="ISO", utc=True)
    console_renderer = _console_renderer()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": console_renderer,
                    "foreign_pre_chain": [
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        timestamper,
                    ],
                }
            },
            "handlers": {
                "default": {
                    "level": level,
                    "class": "logging.StreamHandler",
                    "formatter": "plain",
                }
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            console_renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
