"""The redactor is belt-and-braces; the codepath above it should not
pass secrets to the logging API. But we test it anyway because the
day someone *does* — accidentally, in a hot fix — is a day we want
the test suite to scream rather than the SOC."""
from __future__ import annotations

import logging

from logging_config import RedactingFilter


def test_redactor_zeroes_authorization_header():
    f = RedactingFilter()
    rec = logging.makeLogRecord({
        "msg": "audit",
        "headers": {"Authorization": "Bearer leaked-token", "X-Other": "fine"},
    })
    f.filter(rec)
    assert rec.headers["Authorization"] == "***"
    assert rec.headers["X-Other"] == "fine"


def test_redactor_handles_nested_dicts_at_top_level():
    f = RedactingFilter()
    rec = logging.makeLogRecord({
        "msg": "audit",
        "context": {"x-api-key": "leaked-key", "fine": "ok"},
    })
    f.filter(rec)
    assert rec.context["x-api-key"] == "***"
    assert rec.context["fine"] == "ok"


def test_redactor_returns_true_so_records_propagate():
    f = RedactingFilter()
    rec = logging.makeLogRecord({"msg": "no-secrets-here"})
    assert f.filter(rec) is True
