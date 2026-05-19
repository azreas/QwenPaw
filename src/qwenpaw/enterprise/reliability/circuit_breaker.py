"""熔断器服务 - 防止级联故障的断路器模式实现。"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict


class CircuitBreakerOpen(Exception):
    """熔断器打开状态异常。

    当熔断器处于打开状态时，调用会被快速失败，直接抛出此异常。
    避免在下游服务已故障时继续发送请求，防止级联故障。
    """

    def __init__(self, key: str, opened_until: float) -> None:
        self.key = key
        self.opened_until = opened_until
        super().__init__(f"Circuit breaker for '{key}' is open until {opened_until}")


@dataclass
class CircuitState:
    """熔断器状态。

    Attributes:
        failures: 连续失败次数
        opened_until: 熔断器打开结束时间戳（秒，Unix time）
    """

    failures: int
    opened_until: float

    @property
    def is_open(self) -> bool:
        """检查熔断器当前是否处于打开状态。"""
        return time.time() < self.opened_until


class CircuitBreakerService:
    """熔断器服务。

    使用断路器模式保护对下游服务的调用，防止级联故障。
    当连续失败达到阈值时，熔断器打开，后续调用快速失败。
    经过冷却期后，熔断器进入半开状态，允许少量请求探测。

    Args:
        failure_threshold: 触发熔断器打开的连续失败次数，默认 5 次
        reset_seconds: 熔断器打开后自动重置的秒数，默认 30 秒
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._circuits: Dict[str, CircuitState] = {}
        self._lock = asyncio.Lock()

    async def call(
        self,
        key: str,
        func: Callable[[], Awaitable[Any]],
    ) -> Any:
        """使用熔断器保护异步函数调用。

        Args:
            key: 熔断器键，用于区分不同的下游服务
            func: 要执行的异步函数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpen: 熔断器打开时抛出
            Exception: 原函数抛出的异常
        """
        async with self._lock:
            state = self._circuits.get(key)

            # 检查熔断器是否打开
            if state is not None and state.is_open:
                raise CircuitBreakerOpen(key, state.opened_until)

        try:
            result = await func()
        except Exception:
            # 记录失败
            async with self._lock:
                state = self._circuits.get(key)
                if state is None:
                    state = CircuitState(failures=0, opened_until=0.0)
                    self._circuits[key] = state

                state.failures += 1

                # 达到阈值时打开熔断器
                if state.failures >= self.failure_threshold:
                    state.opened_until = time.time() + self.reset_seconds

            raise

        # 成功时重置熔断器
        async with self._lock:
            state = self._circuits.get(key)
            if state is None:
                # 首次成功，初始化状态
                self._circuits[key] = CircuitState(failures=0, opened_until=0.0)
            else:
                state.failures = 0
                state.opened_until = 0.0

        return result

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器的状态快照。

        Returns:
            字典，key 为熔断器键，value 为包含 failures、opened_until、is_open 的状态字典
        """
        now = time.time()
        return {
            key: {
                "failures": state.failures,
                "opened_until": state.opened_until,
                "is_open": now < state.opened_until,
            }
            for key, state in self._circuits.items()
        }
