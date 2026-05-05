"""JSON access + application logging.

Two logger trees:
  * app.* — application messages
  * app.access — middleware-emitted access logs

Both go through the same JSON formatter so logs ship as one unified
stream. We deliberately do not log request headers; doing so is the
single fastest way to leak a Bearer token into your aggregator."""
from __future__ import annotations

import logging
import logging.config


_REDACT_FIELDS = ("authorization", "x-api-key", "cookie", "set-cookie")


class RedactingFilter(logging.Filter):
    """Belt-and-braces redactor.

    The codepath above this should not be passing secrets through the
    logging API anyway, but if some helper does (`extra={'headers': h}`),
    we replace recognised keys with `***`. Not a substitute for not
    passing secrets in the first place."""

    def filter(self, record: logging.LogRecord) -> bool:
        for attr_name in dir(record):
            if attr_name.startswith("_"):
                continue
            value = getattr(record, attr_name, None)
            if isinstance(value, dict):
                for k in list(value):
                    if k.lower() in _REDACT_FIELDS:
                        value[k] = "***"
        return True


def configure_logging(level: str = "INFO") -> None:
    config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s "
                       "%(request_id)s %(user_id)s",
            },
        },
        "filters": {"redact": {"()": RedactingFilter}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["redact"],
            },
        },
        "root": {"level": level, "handlers": ["stdout"]},
    }
    logging.config.dictConfig(config)
    # python-json-logger reads `extra` keys; if a record doesn't supply
    # request_id/user_id, the formatter would put `null`. We initialise
    # an emoji-free dummy here.
    for h in logging.getLogger().handlers:
        old = h.format
        def format_with_defaults(record: logging.LogRecord, _old=old) -> str:
            for k in ("request_id", "user_id"):
                if not hasattr(record, k):
                    setattr(record, k, "-")
            return _old(record)
        h.format = format_with_defaults  # type: ignore[assignment]
