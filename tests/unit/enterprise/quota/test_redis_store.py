import pytest

from qwenpaw.enterprise.quota.redis_store import RedisQuotaStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expire_calls = []

    async def incrby(self, key, amount):
        self.values[key] = self.values.get(key, 0) + amount
        return self.values[key]

    async def expire(self, key, ttl):
        self.expire_calls.append((key, ttl))

    async def eval(self, script, numkeys, key, limit, ttl):
        value = self.values.get(key, 0)
        if value >= int(limit):
            return 0
        self.values[key] = value + 1
        return 1

    async def decr(self, key):
        self.values[key] = max(0, self.values.get(key, 0) - 1)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_redis_store_increment_sets_expire():
    client = FakeRedis()
    store = RedisQuotaStore(client)

    assert await store.increment("k", amount=2, ttl_seconds=60) == 2
    assert client.expire_calls == [("k", 60)]
