from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from qwenpaw.enterprise.context import get_current_request_context


class EnterpriseJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = get_current_request_context()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(ctx, "request_id", "") if ctx else "",
            "trace_id": getattr(ctx, "trace_id", "") if ctx else "",
            "tenant_id": getattr(ctx, "tenant_id", "") if ctx else "",
            "agent_id": getattr(ctx, "agent_id", "") if ctx else "",
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
