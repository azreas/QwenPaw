# -*- coding: utf-8 -*-
"""API routers."""

from fastapi import APIRouter

from .agents import router as agents_router
from .config import router as config_router
from .local_models import router as local_models_router
from .providers import router as providers_router
from .skills import router as skills_router
from .skills_stream import router as skills_stream_router
from .workspace import router as workspace_router
from .envs import router as envs_router
from .mcp import router as mcp_router
from .mcp_oauth import router as mcp_oauth_router
from .tools import router as tools_router
from ..crons.api import router as cron_router
from ..runner.api import router as runner_router
from .console import router as console_router
from .token_usage import router as token_usage_router
from .agent_stats import router as agent_stats_router
from .auth import router as auth_router
from .messages import router as messages_router
from .files import router as files_router
from .settings import router as settings_router
from .webchat import router as webchat_router
from .platform_tenancy import router as platform_tenancy_router
from .webchat_capabilities import router as webchat_capabilities_router
from .webchat_tasks import router as webchat_tasks_router
from .plugins import router as plugins_router
from .backup import router as backup_router
from .plan import router as plan_router
from .wecom_tenant_management import router as wecom_tenant_management_router
from .wecom_tenant_config import router as wecom_tenant_config_router
from .audit import router as audit_router
from .enterprise_readiness import router as enterprise_readiness_router
from .evaluation import router as evaluation_router
from .quota import router as quota_router

router = APIRouter()

router.include_router(agents_router)
router.include_router(config_router)
router.include_router(console_router)
router.include_router(cron_router)
router.include_router(local_models_router)
router.include_router(mcp_router)
router.include_router(mcp_oauth_router)
router.include_router(messages_router)
router.include_router(providers_router)
router.include_router(runner_router)
router.include_router(skills_router)
router.include_router(skills_stream_router)
router.include_router(tools_router)
router.include_router(workspace_router)
router.include_router(envs_router)
router.include_router(token_usage_router)
router.include_router(agent_stats_router)
router.include_router(auth_router)
router.include_router(files_router)
router.include_router(settings_router)
router.include_router(webchat_router)
router.include_router(platform_tenancy_router)
router.include_router(webchat_capabilities_router)
router.include_router(webchat_tasks_router)
router.include_router(plugins_router)
router.include_router(backup_router)
router.include_router(plan_router)
router.include_router(wecom_tenant_management_router)
router.include_router(wecom_tenant_config_router)
router.include_router(audit_router)
router.include_router(enterprise_readiness_router)
router.include_router(evaluation_router)
router.include_router(quota_router)


def create_agent_scoped_router() -> APIRouter:
    """Create agent-scoped router that wraps existing routers.

    Returns:
        APIRouter with all routers mounted under /agents/{agentId}/
    """
    from .agent_scoped import create_agent_scoped_router as _create

    return _create()


__all__ = ["router", "create_agent_scoped_router"]
