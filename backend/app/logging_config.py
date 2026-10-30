import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log aggregation in deployed environments."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if json_logs
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    app_logger = logging.getLogger("app")
    app_logger.handlers = [handler]
    app_logger.setLevel(level.upper())
    app_logger.propagate = False
