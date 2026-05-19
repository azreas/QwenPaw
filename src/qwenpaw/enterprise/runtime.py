from __future__ import annotations

from dataclasses import dataclass, field

from .authz.service import AuthzService
from .interfaces import (
    AuditEventBusProtocol,
    AuthzServiceProtocol,
    HealthServiceProtocol,
    ObservabilityServiceProtocol,
    PolicyServiceProtocol,
    QuotaServiceProtocol,
    RuntimeExtensionResolverProtocol,
    StorageManagerProtocol,
)
from .observability.service import ObservabilityService
from .reliability.circuit_breaker import CircuitBreakerService
from .reliability.dead_letter import InMemoryDeadLetterQueue, RedisDeadLetterQueue
from .reliability.health import HealthService
from .policy import PolicyService
from .quota.config import QuotaConfig
from .quota.redis_store import RedisQuotaStore
from .quota.service import QuotaService
from .quota.store import InMemoryQuotaStore
from .noop import (
    NoopAuditEventBus,
    NoopRuntimeExtensionResolver,
    NoopStorageManager,
)
from .storage.config import StorageConfig
from .storage.manager import StorageManager


@dataclass
class EnterpriseRuntime:
    storage: StorageManagerProtocol = field(default_factory=NoopStorageManager)
    authz: AuthzServiceProtocol = field(default_factory=AuthzService)
    audit: AuditEventBusProtocol = field(default_factory=NoopAuditEventBus)
    extensions: RuntimeExtensionResolverProtocol = field(
        default_factory=NoopRuntimeExtensionResolver
    )
    policy: PolicyServiceProtocol = field(default_factory=PolicyService)
    observability: ObservabilityServiceProtocol = field(default_factory=ObservabilityService)
    quota: QuotaServiceProtocol | None = None
    health: HealthServiceProtocol | None = None
    circuit_breaker: CircuitBreakerService = field(default_factory=CircuitBreakerService)
    dead_letter: InMemoryDeadLetterQueue = field(default_factory=InMemoryDeadLetterQueue)
    started: bool = False

    async def start(self) -> None:
        await self.storage.start()
        if hasattr(self.audit, "start"):
            await self.audit.start()  # type: ignore[attr-defined]
        if hasattr(self.quota, "start"):
            await self.quota.start()  # type: ignore[attr-defined]
        if hasattr(self.observability, "start"):
            await self.observability.start()  # type: ignore[attr-defined]
        self.started = True

    async def stop(self) -> None:
        if hasattr(self.audit, "stop"):
            await self.audit.stop()  # type: ignore[attr-defined]
        if hasattr(self.quota, "stop"):
            await self.quota.stop()  # type: ignore[attr-defined]
        if hasattr(self.observability, "stop"):
            await self.observability.stop()  # type: ignore[attr-defined]
        if hasattr(self.storage, "stop"):
            await self.storage.stop()
        if hasattr(self.dead_letter, "close"):
            await self.dead_letter.close()  # type: ignore[attr-defined]
        self.started = False


def create_enterprise_runtime() -> EnterpriseRuntime:
    """构造企业运行时，注入 StorageConfig.from_env() 驱动的 StorageManager 和 AuthzService。

    SQL storage 启用时自动创建 AuditEventBus（含 repository + spool）。
    始终创建 RuntimeExtensionResolver（非 Noop），以便后台插件加载后
    可以及时注入 provider，避免竞态。

    如果 QWENPAW_SANDBOX_ENABLED=true 且 QWENPAW_SANDBOX_GATEWAY_URL
    已设置，则在 resolver 中预注册 SandboxRuntimeExtensionProvider，
    确保首个请求在插件加载前也能获取沙箱策略。
    """
    import os
    from pathlib import Path

    from .extensions.resolver import RuntimeExtensionResolver

    config = StorageConfig.from_env()
    storage: StorageManagerProtocol = StorageManager(config)
    authz: AuthzServiceProtocol = AuthzService()
    extensions = RuntimeExtensionResolver()
    policy: PolicyServiceProtocol = PolicyService()
    observability: ObservabilityServiceProtocol = ObservabilityService()

    quota_config = QuotaConfig.from_env()
    quota_service: QuotaService | None = None
    dead_letter: InMemoryDeadLetterQueue | RedisDeadLetterQueue = InMemoryDeadLetterQueue()
    if quota_config.enabled:
        quota_store = (
            RedisQuotaStore.from_url(quota_config.redis_url)
            if quota_config.redis_url
            else InMemoryQuotaStore()
        )
        quota_service = QuotaService(
            store=quota_store,
            limits=quota_config.default_limits,
        )
        # 复用 quota 的 Redis URL 创建死信队列客户端
        if quota_config.redis_url:
            dead_letter = RedisDeadLetterQueue.from_url(quota_config.redis_url)

    # 预注册策略 provider（默认启用）
    from .policy.provider import PolicyRuntimeExtensionProvider

    extensions.register_provider(PolicyRuntimeExtensionProvider(policy=policy))

    # 预注册沙箱 provider（如果环境变量启用）
    _sandbox_enabled = os.environ.get(
        "QWENPAW_SANDBOX_ENABLED", ""
    ).lower() in {"true", "1", "yes"}
    _sandbox_url = os.environ.get("QWENPAW_SANDBOX_GATEWAY_URL", "")
    if _sandbox_enabled and _sandbox_url:
        from ..plugins.sandbox_runtime.config import (
            SandboxRuntimeConfig,
        )
        from ..plugins.sandbox_runtime.provider import (
            SandboxRuntimeExtensionProvider,
        )

        sandbox_config = SandboxRuntimeConfig(
            enabled=True, gateway_url=_sandbox_url
        )
        extensions.register_provider(
            SandboxRuntimeExtensionProvider(sandbox_config)
        )

    audit_bus = None
    if config.enabled and isinstance(storage, StorageManager):
        from .audit.repository import AuditRepository
        from .audit.spool import AuditSpool
        from .audit.event_bus import AuditEventBus

        from ..constant import WORKING_DIR

        spool_dir = Path(WORKING_DIR) / "audit-spool"
        spool = AuditSpool(spool_dir)
        repository = AuditRepository(storage)
        audit_bus = AuditEventBus(repository=repository, spool=spool)

    health = HealthService(
        storage=storage,
        audit=audit_bus,
        observability=observability,
        quota=quota_service,
        extensions=extensions,
    )

    if audit_bus is not None:
        return EnterpriseRuntime(
            storage=storage,
            authz=authz,
            audit=audit_bus,
            extensions=extensions,
            policy=policy,
            observability=observability,
            quota=quota_service,
            health=health,
            dead_letter=dead_letter,
        )

    return EnterpriseRuntime(
        storage=storage,
        authz=authz,
        extensions=extensions,
        policy=policy,
        observability=observability,
        quota=quota_service,
        health=health,
        dead_letter=dead_letter,
    )
