"""熔断器服务单元测试。"""

import asyncio
import time

import pytest

from qwenpaw.enterprise.reliability.circuit_breaker import (
    CircuitBreakerOpen,
    CircuitBreakerService,
    CircuitState,
)


class TestCircuitState:
    """测试 CircuitState 数据类。"""

    def test_is_open_when_opened_until_in_future(self) -> None:
        """opened_until 在未来时应返回打开状态。"""
        state = CircuitState(failures=3, opened_until=time.time() + 10)
        assert state.is_open is True

    def test_is_open_when_opened_until_in_past(self) -> None:
        """opened_until 在过去时应返回关闭状态。"""
        state = CircuitState(failures=3, opened_until=time.time() - 10)
        assert state.is_open is False

    def test_is_open_when_opened_until_zero(self) -> None:
        """opened_until 为 0 时应返回关闭状态。"""
        state = CircuitState(failures=0, opened_until=0.0)
        assert state.is_open is False


class TestCircuitBreakerService:
    """测试 CircuitBreakerService。"""

    @pytest.mark.asyncio
    async def test_successful_call_resets_failures(self) -> None:
        """成功调用应重置失败计数。"""
        cb = CircuitBreakerService(failure_threshold=3, reset_seconds=30)

        async def succeed() -> str:
            return "success"

        result = await cb.call("service_a", succeed)
        assert result == "success"

        snapshot = cb.snapshot()
        assert "service_a" in snapshot
        assert snapshot["service_a"]["failures"] == 0
        assert snapshot["service_a"]["is_open"] is False

    @pytest.mark.asyncio
    async def test_failure_increments_failures_count(self) -> None:
        """失败调用应增加失败计数。"""
        cb = CircuitBreakerService(failure_threshold=3, reset_seconds=30)

        async def fail() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await cb.call("service_b", fail)

        snapshot = cb.snapshot()
        assert "service_b" in snapshot
        assert snapshot["service_b"]["failures"] == 1
        assert snapshot["service_b"]["is_open"] is False

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        """达到失败达到阈值后应打开熔断器。"""
        cb = CircuitBreakerService(failure_threshold=2, reset_seconds=30)

        async def fail() -> None:
            raise ValueError("test error")

        # 第一次失败
        with pytest.raises(ValueError):
            await cb.call("service_c", fail)
        assert cb.snapshot()["service_c"]["failures"] == 1

        # 第二次失败 - 达到阈值
        with pytest.raises(ValueError):
            await cb.call("service_c", fail)

        # 熔断器已打开
        snapshot = cb.snapshot()
        assert snapshot["service_c"]["failures"] == 2
        assert snapshot["service_c"]["is_open"] is True
        assert snapshot["service_c"]["opened_until"] > time.time()

        # 再次调用应抛出 CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await cb.call("service_c", fail)
        assert exc_info.value.key == "service_c"

    @pytest.mark.asyncio
    async def test_resets_after_successful_call(self) -> None:
        """成功调用应重置之前的失败计数。"""
        cb = CircuitBreakerService(failure_threshold=3, reset_seconds=30)

        async def fail() -> None:
            raise ValueError("test error")

        async def succeed() -> str:
            return "ok"

        # 失败 2 次
        with pytest.raises(ValueError):
            await cb.call("service_d", fail)
        with pytest.raises(ValueError):
            await cb.call("service_d", fail)

        assert cb.snapshot()["service_d"]["failures"] == 2

        # 成功调用 - 重置计数
        await cb.call("service_d", succeed)

        assert cb.snapshot()["service_d"]["failures"] == 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self) -> None:
        """不同键的熔断器应相互独立。"""
        cb = CircuitBreakerService(failure_threshold=2, reset_seconds=30)

        async def fail() -> None:
            raise ValueError("test error")

        async def succeed() -> str:
            return "ok"

        # service_e 失败 2 次 - 打开
        with pytest.raises(ValueError):
            await cb.call("service_e", fail)
        with pytest.raises(ValueError):
            await cb.call("service_e", fail)

        # service_f 成功
        await cb.call("service_f", succeed)

        snapshot = cb.snapshot()
        assert snapshot["service_e"]["is_open"] is True
        assert snapshot["service_f"]["is_open"] is False

    @pytest.mark.asyncio
    async def test_closes_after_reset_timeout(self) -> None:
        """重置时间过后熔断器应关闭。"""
        cb = CircuitBreakerService(failure_threshold=2, reset_seconds=0.1)

        async def fail() -> None:
            raise ValueError("test error")

        # 打开熔断器
        with pytest.raises(ValueError):
            await cb.call("service_g", fail)
        with pytest.raises(ValueError):
            await cb.call("service_g", fail)

        assert cb.snapshot()["service_g"]["is_open"] is True

        # 等待重置
        await asyncio.sleep(0.15)

        # 熔断器应关闭，可再次调用
        async def succeed() -> str:
            return "ok"

        result = await cb.call("service_g", succeed)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_empty_snapshot(self) -> None:
        """空熔断器快照应为空字典。"""
        cb = CircuitBreakerService()
        assert cb.snapshot() == {}

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_exception(self) -> None:
        """测试 CircuitBreakerOpen 异常属性。"""
        cb = CircuitBreakerService(failure_threshold=1, reset_seconds=30)

        async def fail() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await cb.call("service_h", fail)

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await cb.call("service_h", fail)

        assert exc_info.value.key == "service_h"
        assert exc_info.value.opened_until > time.time()
        assert "service_h" in str(exc_info.value)
