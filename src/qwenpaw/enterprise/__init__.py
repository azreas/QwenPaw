"""企业运行时脊柱 — RequestContext、服务 Protocol、Noop 默认实现、EnterpriseRuntime。"""

from .context import RequestContext, RequestActor
from .interfaces import (
    AuthzDecision,
    AuditEventBusProtocol,
    AuthzServiceProtocol,
    PolicyServiceProtocol,
    QuotaServiceProtocol,
    RuntimeExtensionBundle,
    RuntimeExtensionResolverProtocol,
    StorageManagerProtocol,
    ToolPolicyPatch,
)
from .middleware import RequestIdentityMiddleware
from .noop import (
    NoopAuditEventBus,
    NoopAuthzService,
    NoopRuntimeExtensionResolver,
    NoopStorageManager,
)
from .runtime import EnterpriseRuntime, create_enterprise_runtime
from .storage import StorageConfig, StorageManager, get_storage_manager_from_app

__all__ = [
    "AuthzDecision",
    "AuditEventBusProtocol",
    "AuthzServiceProtocol",
    "EnterpriseRuntime",
    "PolicyServiceProtocol",
    "QuotaServiceProtocol",
    "NoopAuditEventBus",
    "NoopAuthzService",
    "NoopRuntimeExtensionResolver",
    "NoopStorageManager",
    "RequestActor",
    "RequestContext",
    "RequestIdentityMiddleware",
    "RuntimeExtensionBundle",
    "RuntimeExtensionResolverProtocol",
    "StorageConfig",
    "StorageManager",
    "StorageManagerProtocol",
    "ToolPolicyPatch",
    "create_enterprise_runtime",
    "get_storage_manager_from_app",
]
