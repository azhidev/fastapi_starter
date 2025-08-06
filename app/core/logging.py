import logging
from logging.config import dictConfig


def setup_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(levelname)s %(asctime)s %(name)s: %(message)s",
                }
            },
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
            "root": {"handlers": ["console"], "level": "INFO"},
        }
    )


logger = logging.getLogger("app")
