"""审计事件总线 — 队列 + 批量写入 + spool fallback + 重放。

可靠性保证：
- emit() 不丢事件：队列满直接写 spool
- consumer 批量写 DB，失败整批写 spool
- stop() drain 队列；drain 失败也写 spool
- replay_spool() 读 spool → 写 DB → ack
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from qwenpaw.enterprise.audit.models import AuditEvent
from qwenpaw.enterprise.audit.spool import AuditSpool

logger = logging.getLogger(__name__)


class AuditRepositoryProtocol(Protocol):
    async def append_many(self, events: list[AuditEvent]) -> None: ...

    async def query(self, **kwargs: Any) -> list: ...


class AuditEventBus:
    """可靠审计事件总线。"""

    def __init__(
        self,
        repository: AuditRepositoryProtocol,
        spool: AuditSpool | None = None,
        queue_size: int = 1024,
        flush_interval_seconds: float = 1.0,
        batch_size: int = 50,
    ) -> None:
        self._repository = repository
        self._spool = spool
        self._queue: asyncio.Queue[AuditEvent] | None = None
        self._queue_size = queue_size
        self._flush_interval = flush_interval_seconds
        self._batch_size = batch_size
        self._consumer_task: asyncio.Task | None = None
        self._replay_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._inflight: list[AuditEvent] = []  # 当前批次，CancelledError 时落 spool
        self._replay_interval = 60  # spool 重放间隔（秒）
        self._shutdown_timeout = 10.0  # 等待 consumer 完成的超时（秒）
        self._running = False

    async def start(self) -> None:
        self._queue = asyncio.Queue(maxsize=self._queue_size)
        self._running = True
        self._stop_event = asyncio.Event()
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        self._replay_task = asyncio.create_task(self._replay_loop())
        # 启动时先重放一轮旧 spool
        await self.replay_spool()

    async def stop(self) -> None:
        self._running = False
        # 唤醒 consumer 使其自然退出，避免 cancel 导致已出队事件丢失
        if self._stop_event is not None:
            self._stop_event.set()
        if self._replay_task is not None:
            self._replay_task.cancel()
            try:
                await self._replay_task
            except asyncio.CancelledError:
                pass

        consumer_timed_out = False
        if self._consumer_task is not None:
            try:
                await asyncio.wait_for(
                    self._consumer_task,
                    timeout=self._shutdown_timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "consumer 关闭超时（%s 秒），残余事件转入 spool",
                    self._shutdown_timeout,
                )
                consumer_timed_out = True
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
        # drain 残余事件
        await self._drain()
        # 最后尝试重放一次 spool（DB 可用前提下）
        if not consumer_timed_out:
            await self.replay_spool()

    async def emit(self, event: AuditEvent) -> None:
        """发送审计事件。队列满时直接写 spool，不丢事件。"""
        if self._queue is None:
            await self._spool_fallback([event])
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("审计队列已满，事件写入 spool")
            await self._spool_fallback([event])

    async def replay_spool(self) -> None:
        """重放 spool 中积压的事件：读 → 写 DB → ack。"""
        if self._spool is None:
            return

        while True:
            batch = await self._spool.read_batch(limit=self._batch_size)
            if not batch.events:
                break
            try:
                await self._repository.append_many(batch.events)
                await self._spool.ack(batch)
                logger.info("spool 重放成功: %d 条事件", len(batch.events))
            except Exception:
                logger.exception("spool 重放失败，保留文件待下次重试")
                break

    async def _consumer_loop(self) -> None:
        """后台消费循环：定时从队列取事件批量写入 DB。

        stop() 通过 _stop_event 唤醒循环，不会 cancel 本 task，
        避免已出队但尚未写入 DB 的事件丢失。
        """
        try:
            while self._running:
                # 等待 flush 间隔到期或 stop 信号
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),  # type: ignore[union-attr]
                        timeout=self._flush_interval,
                    )
                except asyncio.TimeoutError:
                    pass  # 超时 = flush 间隔到，继续处理

                self._inflight = self._drain_queue()
                if not self._inflight:
                    continue

                try:
                    await self._repository.append_many(self._inflight)
                    self._inflight = []
                except Exception:
                    logger.exception("审计 DB 写入失败，事件转入 spool")
                    await self._spool_fallback(self._inflight)
                    self._inflight = []
        except asyncio.CancelledError:
            if self._inflight:
                await self._spool_fallback(self._inflight)
                self._inflight = []
            events = self._drain_queue()
            if events:
                await self._spool_fallback(events)
            raise

    async def _replay_loop(self) -> None:
        """后台定期重放 spool 中积压的事件。"""
        while self._running:
            try:
                await asyncio.sleep(self._replay_interval)
            except asyncio.CancelledError:
                break
            try:
                await self.replay_spool()
            except Exception:
                logger.exception("spool 定期重放失败")

    def _drain_queue(self) -> list[AuditEvent]:
        """从队列中取出当前积压的事件（最多 batch_size 条）。"""
        if self._queue is None:
            return []
        events: list[AuditEvent] = []
        for _ in range(self._batch_size):
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events

    async def _drain(self) -> None:
        """停止时 drain 队列中的所有残余事件。"""
        events = self._drain_queue()
        # 继续取直到队列清空
        if self._queue is not None:
            while not self._queue.empty():
                try:
                    events.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

        if not events:
            return

        try:
            await self._repository.append_many(events)
        except Exception:
            logger.exception("审计 drain 写入失败，事件转入 spool")
            await self._spool_fallback(events)

    async def _spool_fallback(self, events: list[AuditEvent]) -> None:
        """将事件写入 fallback spool。"""
        if self._spool is None:
            logger.error("审计事件丢失: spool 未配置, %d 条事件", len(events))
            return
        try:
            await self._spool.write_many(events)
        except Exception:
            logger.exception("审计 spool 写入失败: %d 条事件丢失", len(events))
