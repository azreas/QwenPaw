import pytest

from qwenpaw.enterprise.quota.store import InMemoryQuotaStore


@pytest.mark.asyncio
async def test_in_memory_store_increments_with_ttl():
    store = InMemoryQuotaStore()

    assert await store.increment("k", amount=2, ttl_seconds=60) == 2
    assert await store.increment("k", amount=3, ttl_seconds=60) == 5


@pytest.mark.asyncio
async def test_in_memory_store_lease_release():
    store = InMemoryQuotaStore()

    lease = await store.acquire_lease("concurrent", limit=1, ttl_seconds=30)
    assert lease.acquired is True
    denied = await store.acquire_lease("concurrent", limit=1, ttl_seconds=30)
    assert denied.acquired is False

    await lease.release()
    allowed = await store.acquire_lease("concurrent", limit=1, ttl_seconds=30)
    assert allowed.acquired is True
