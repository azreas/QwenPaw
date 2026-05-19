from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LeaseRelease(Protocol):
    async def __call__(self) -> None: ...


@dataclass(slots=True)
class QuotaLease:
    acquired: bool
    release: LeaseRelease


class QuotaCounterStoreProtocol(Protocol):
    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int: ...
    async def acquire_lease(
        self,
        key: str,
        limit: int,
        ttl_seconds: int,
    ) -> QuotaLease: ...
    async def close(self) -> None: ...


class InMemoryQuotaStore:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}

    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        self._values[key] = self._values.get(key, 0) + amount
        return self._values[key]

    async def acquire_lease(
        self,
        key: str,
        limit: int,
        ttl_seconds: int,
    ) -> QuotaLease:
        current = self._values.get(key, 0)
        if current >= limit:
            async def noop() -> None:
                return None

            return QuotaLease(acquired=False, release=noop)

        self._values[key] = current + 1

        async def release() -> None:
            self._values[key] = max(0, self._values.get(key, 0) - 1)

        return QuotaLease(acquired=True, release=release)

    async def close(self) -> None:
        self._values.clear()
