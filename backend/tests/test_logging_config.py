import json
import logging

from app.logging_config import JsonFormatter, configure_logging


def test_json_formatter_emits_parseable_line():
    record = logging.LogRecord("app.x", logging.WARNING, __file__, 1, "hello %s", ("world",), None)
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "hello world"
    assert entry["level"] == "WARNING"
    assert entry["logger"] == "app.x"


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord("app.x", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]


def test_configure_logging_sets_level_and_handler():
    configure_logging("debug", json_logs=True)
    app_logger = logging.getLogger("app")
    assert app_logger.level == logging.DEBUG
    assert isinstance(app_logger.handlers[0].formatter, JsonFormatter)
    configure_logging("INFO")
