"""`JSONFormatter` n'est branché qu'en production (voir `config.settings.
prod`) : on l'exerce directement ici plutôt que de changer de réglages."""

import json
import logging
import sys

from apps.core.logging import JSONFormatter


def _make_record(**extra):
    record = logging.LogRecord(
        name="security",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="login_failed",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_produces_valid_json_with_expected_fields():
    record = _make_record(event="login_failed", ip="203.0.113.5")
    payload = json.loads(JSONFormatter().format(record))

    assert payload["level"] == "WARNING"
    assert payload["logger"] == "security"
    assert payload["message"] == "login_failed"
    assert payload["event"] == "login_failed"
    assert payload["ip"] == "203.0.113.5"
    assert "timestamp" in payload


def test_json_formatter_excludes_standard_logrecord_attributes():
    record = _make_record()
    payload = json.loads(JSONFormatter().format(record))

    for standard_key in ("pathname", "lineno", "funcName", "msg", "args", "levelno"):
        assert standard_key not in payload


def test_json_formatter_includes_exception_traceback():
    try:
        raise ValueError("une erreur de test")
    except ValueError:
        exc_info = sys.exc_info()

    record = _make_record()
    record.exc_info = exc_info
    payload = json.loads(JSONFormatter().format(record))

    assert "une erreur de test" in payload["exc_info"]


def test_json_formatter_never_crashes_on_non_serializable_extra_values():
    class Weird:
        def __str__(self):
            return "weird-object"

    record = _make_record(custom=Weird())
    payload = json.loads(JSONFormatter().format(record))
    assert payload["custom"] == "weird-object"
