"""死信队列 - 记录失败任务以便后续重试。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import DeadLetterMessage


class InMemoryDeadLetterQueue:
    """内存中的死信队列实现。

    用于记录执行失败的任务（如 Cron、通知等），
    支持后续手动或自动重试。
    """

    def __init__(self) -> None:
        self._messages: dict[str, DeadLetterMessage] = {}

    async def append(
        self,
        *,
        source: str,
        payload: dict,
        error: str,
    ) -> DeadLetterMessage:
        """追加一条失败消息。"""
        message = DeadLetterMessage(
            id=uuid4().hex,
            source=source,
            payload=payload,
            error=error,
        )
        self._messages[message.id] = message
        return message

    async def list_messages(self, source: str | None = None) -> list[DeadLetterMessage]:
        """列出所有消息。"""
        values = list(self._messages.values())
        if source is not None:
            values = [message for message in values if message.source == source]
        return values

    async def ack(self, message_id: str) -> bool:
        """确认并删除消息。"""
        return self._messages.pop(message_id, None) is not None

    async def close(self) -> None:
        """清理资源。"""
        self._messages.clear()

    async def healthcheck(self) -> dict[str, Any]:
        """健康检查 - 内存实现始终正常。"""
        return {"status": "ok", "backend": "memory"}


class RedisDeadLetterQueue:
    """Redis 死信队列实现 - 持久化存储，重启不丢失。"""

    DLQ_KEY_PREFIX = "dlq:message:"
    DLQ_SOURCE_INDEX_PREFIX = "dlq:source:"

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisDeadLetterQueue":
        """从 Redis URL 构造实例。"""
        from redis import asyncio as redis_asyncio

        return cls(redis_asyncio.from_url(redis_url, decode_responses=True))

    async def append(
        self,
        *,
        source: str,
        payload: dict,
        error: str,
    ) -> DeadLetterMessage:
        """追加一条失败消息。"""
        message_id = uuid4().hex
        message = DeadLetterMessage(
            id=message_id,
            source=source,
            payload=payload,
            error=error,
        )

        message_key = f"{self.DLQ_KEY_PREFIX}{message_id}"
        source_key = f"{self.DLQ_SOURCE_INDEX_PREFIX}{source}"

        # 存储消息详情
        await self._client.hset(
            message_key,
            mapping={
                "id": message.id,
                "source": message.source,
                "payload": json.dumps(message.payload, ensure_ascii=False),
                "error": message.error,
                "attempts": message.attempts,
                "created_at": message.created_at.isoformat(),
            },
        )
        # 添加到 source 索引
        await self._client.sadd(source_key, message_id)
        # 设置过期时间（默认 30 天）
        await self._client.expire(message_key, 30 * 24 * 3600)
        await self._client.expire(source_key, 30 * 24 * 3600)

        return message

    async def list_messages(self, source: str | None = None) -> list[DeadLetterMessage]:
        """列出所有消息。"""
        if source is not None:
            source_key = f"{self.DLQ_SOURCE_INDEX_PREFIX}{source}"
            message_ids = await self._client.smembers(source_key)
        else:
            all_keys = await self._client.keys(f"{self.DLQ_KEY_PREFIX}*")
            message_ids = [k.removeprefix(self.DLQ_KEY_PREFIX) for k in all_keys]

        messages: list[DeadLetterMessage] = []
        for message_id in message_ids:
            message_key = f"{self.DLQ_KEY_PREFIX}{message_id}"
            data = await self._client.hgetall(message_key)
            if data:
                messages.append(
                    DeadLetterMessage(
                        id=data["id"],
                        source=data["source"],
                        payload=json.loads(data["payload"]),
                        error=data["error"],
                        attempts=int(data.get("attempts", 0)),
                        created_at=datetime.fromisoformat(data["created_at"]).replace(tzinfo=timezone.utc),
                    )
                )

        return sorted(messages, key=lambda m: m.created_at)

    async def ack(self, message_id: str) -> bool:
        """确认并删除消息。"""
        message_key = f"{self.DLQ_KEY_PREFIX}{message_id}"

        # 先获取 source，以便从索引中移除
        source = await self._client.hget(message_key, "source")
        if source is None:
            return False

        source_key = f"{self.DLQ_SOURCE_INDEX_PREFIX}{source}"

        # 删除消息和索引中的引用
        await self._client.delete(message_key)
        await self._client.srem(source_key, message_id)

        return True

    async def close(self) -> None:
        """关闭 Redis 连接。"""
        await self._client.close()

    async def healthcheck(self) -> dict[str, Any]:
        """Redis 后端健康检查 - 通过 ping 验证连接。"""
        try:
            await self._client.ping()
            return {"status": "ok", "backend": "redis"}
        except Exception as exc:
            return {"status": "error", "backend": "redis", "message": str(exc)}
