from __future__ import annotations

from .metrics import MetricsRegistry


class ObservabilityService:
    def __init__(self, metrics: MetricsRegistry | None = None) -> None:
        self.metrics = metrics or MetricsRegistry()
        self.started = False

    async def start(self) -> None:
        self.started = True
        self.record_event("runtime_component_started_total", labels={"component": "observability"})

    async def stop(self) -> None:
        self.started = False

    def record_event(self, name: str, labels: dict[str, str] | None = None) -> None:
        self.metrics.inc(name, labels=labels)
