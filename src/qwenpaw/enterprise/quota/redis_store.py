from __future__ import annotations

from typing import Any

from .store import QuotaLease

_ACQUIRE_LEASE_SCRIPT = """
local current = tonumber(redis.call('get', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then
  return 0
end
redis.call('incr', KEYS[1])
redis.call('expire', KEYS[1], tonumber(ARGV[2]))
return 1
"""


class RedisQuotaStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisQuotaStore":
        from redis import asyncio as redis_asyncio

        return cls(redis_asyncio.from_url(redis_url, decode_responses=True))

    async def increment(self, key: str, amount: int, ttl_seconds: int) -> int:
        value = await self._client.incrby(key, amount)
        await self._client.expire(key, ttl_seconds)
        return int(value)

    async def acquire_lease(
        self,
        key: str,
        limit: int,
        ttl_seconds: int,
    ) -> QuotaLease:
        acquired = bool(
            await self._client.eval(
                _ACQUIRE_LEASE_SCRIPT,
                1,
                key,
                limit,
                ttl_seconds,
            )
        )

        async def release() -> None:
            if acquired:
                await self._client.decr(key)

        return QuotaLease(acquired=acquired, release=release)

    async def close(self) -> None:
        await self._client.close()
