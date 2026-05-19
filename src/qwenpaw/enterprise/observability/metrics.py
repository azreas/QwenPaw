from __future__ import annotations

from collections import defaultdict
from threading import RLock

from .models import MetricSample, MetricType

_DENIED_LABELS = {"user_id", "session_id", "request_id", "trace_id"}


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._types: dict[str, MetricType] = {}

    def inc(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        self._record(name, MetricType.COUNTER, amount, labels, increment=True)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._record(name, MetricType.GAUGE, value, labels, increment=False)

    def samples(self) -> list[MetricSample]:
        with self._lock:
            return [
                MetricSample(name=name, value=value, metric_type=self._types[name], labels=dict(labels))
                for (name, labels), value in sorted(self._values.items())
            ]

    def _record(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        labels: dict[str, str] | None,
        *,
        increment: bool,
    ) -> None:
        clean_labels = self._normalize_labels(labels or {})
        key = (name, tuple(sorted(clean_labels.items())))
        with self._lock:
            self._types[name] = metric_type
            if increment:
                self._values[key] += value
            else:
                self._values[key] = value

    def to_prometheus_text(self) -> str:
        lines: list[str] = []
        for sample in self.samples():
            labels = ",".join(
                f'{key}="{value}"' for key, value in sorted(sample.labels.items())
            )
            suffix = f"{{{labels}}}" if labels else ""
            lines.append(f"{sample.name}{suffix} {sample.value}")
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _normalize_labels(labels: dict[str, str]) -> dict[str, str]:
        denied = _DENIED_LABELS & set(labels)
        if denied:
            raise ValueError(f"high-cardinality labels are not allowed: {sorted(denied)}")
        return {str(k): str(v) for k, v in labels.items()}
