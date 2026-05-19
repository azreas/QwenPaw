# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
import inspect
import asyncio
import mimetypes
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from agentscope_runtime.engine.app import AgentApp
from agentscope_runtime.engine.schemas.exception import (
    AppBaseException,
)

from ..config import load_config  # pylint: disable=no-name-in-module
from ..config.utils import get_config_path
from ..constant import (
    DOCS_ENABLED,
    LOG_LEVEL_ENV,
    CORS_ORIGINS,
    WORKING_DIR,
    PROJECT_NAME,
)
from ..__version__ import __version__
from ..backup._utils.safe_swap import cleanup_startup_restore_artifacts
from ..utils.logging import (
    setup_logger,
    add_project_file_handler,
    LOG_FILE_PATH,
)
from ..utils.system_info import summarize_python_environment
from .auth import AuthMiddleware, auto_register_from_env
from .routers import router as api_router, create_agent_scoped_router
from .routers.agent_scoped import AgentContextMiddleware
from .routers.approval import router as approval_router
from .routers.voice import voice_router
from ..envs import load_envs_into_environ
from ..providers.provider_manager import ProviderManager
from ..local_models.manager import LocalModelManager
from .multi_agent_manager import MultiAgentManager
from .migration import (
    migrate_legacy_workspace_to_default_agent,
    migrate_legacy_skills_to_skill_pool,
    ensure_default_agent_exists,
    ensure_qa_agent_exists,
)
from .channels.registry import register_custom_channel_routes

# Apply log level on load so reload child process gets same level as CLI.
logger = setup_logger(os.environ.get(LOG_LEVEL_ENV, "info"))

# Ensure static assets are served with browser-compatible MIME types across
# platforms (notably Windows may miss .js/.mjs mappings).
mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/wasm", ".wasm")

# Load persisted env vars into os.environ at module import time
# so they are available before the lifespan starts.
load_envs_into_environ()


# Dynamic runner that selects the correct workspace runner based on request
class DynamicMultiAgentRunner:
    """Runner wrapper that dynamically routes to the correct workspace runner.

    This allows AgentApp to work with multiple agents by inspecting
    the X-Agent-Id header on each request.
    """

    def __init__(self):
        self.framework_type = "agentscope"
        self._multi_agent_manager = None

    def set_multi_agent_manager(self, manager):
        """Set the MultiAgentManager instance after initialization."""
        self._multi_agent_manager = manager

    async def _get_workspace(self, request):
        """Get the correct workspace based on request.

        Returns:
            Workspace: The workspace instance for the current agent.
        """
        from .agent_context import get_current_agent_id

        # Get agent_id from context (set by middleware or header)
        agent_id = get_current_agent_id()

        logger.debug(f"_get_workspace: agent_id={agent_id}")

        # Get the correct workspace
        if not self._multi_agent_manager:
            raise RuntimeError("MultiAgentManager not initialized")

        try:
            workspace = await self._multi_agent_manager.get_agent(agent_id)
            logger.debug(
                "Got workspace: %s, runner: %s",
                workspace.agent_id,
                workspace.runner,
            )
            return workspace
        except (ValueError, AppBaseException) as e:
            logger.error(f"Agent not found: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Error getting workspace: {e}",
                exc_info=True,
            )
            raise

    async def _get_workspace_runner(self, request):
        """Get the correct workspace runner based on request."""
        workspace = await self._get_workspace(request)
        return workspace.runner

    async def stream_query(self, request, *args, **kwargs):
        """Dynamically route to the correct workspace runner.

        Registers the task with the workspace's TaskTracker so that
        graceful shutdown during agent reload can detect in-flight
        background tasks (fixes #3275).
        """
        logger.debug("DynamicMultiAgentRunner.stream_query called")
        workspace = None
        run_key = None
        try:
            workspace = await self._get_workspace(request)
            runner = workspace.runner
            logger.debug(f"Got runner: {runner}, type: {type(runner)}")

            # Register this task with the workspace's TaskTracker so
            # _graceful_stop_old_instance() can see it during reload.
            run_key = f"ext-{uuid.uuid4().hex}"
            await workspace.task_tracker.register_external_task(run_key)

            # Delegate to the actual runner's stream_query generator
            count = 0
            async for item in runner.stream_query(request, *args, **kwargs):
                count += 1
                logger.debug(f"Yielding item #{count}: {type(item)}")
                yield item
            logger.debug(f"stream_query completed, yielded {count} items")
        except Exception as e:
            logger.error(
                f"Error in stream_query: {e}",
                exc_info=True,
            )
            # Yield error message to client
            yield {
                "error": str(e),
                "type": "error",
            }
        finally:
            # Always unregister the task when done (success, error,
            # or cancellation).
            if workspace is not None and run_key is not None:
                await workspace.task_tracker.unregister_external_task(run_key)

    async def query_handler(self, request, *args, **kwargs):
        """Dynamically route to the correct workspace runner.

        Registers the task with the workspace's TaskTracker so that
        graceful shutdown during agent reload can detect in-flight
        requests (fixes #3275).
        """
        workspace = None
        run_key = None
        try:
            workspace = await self._get_workspace(request)
            runner = workspace.runner

            run_key = f"ext-{uuid.uuid4().hex}"
            await workspace.task_tracker.register_external_task(run_key)

            async for item in runner.query_handler(request, *args, **kwargs):
                yield item
        finally:
            # Always unregister the task when done (success, error,
            # or cancellation).
            if workspace is not None and run_key is not None:
                await workspace.task_tracker.unregister_external_task(run_key)

    # Async context manager support for AgentApp lifecycle
    async def __aenter__(self):
        """
        No-op context manager entry (workspaces manage their own runners).
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """No-op context manager exit (workspaces manage their own runners)."""
        return None


# Use dynamic runner for AgentApp
runner = DynamicMultiAgentRunner()

agent_app = AgentApp(
    app_name="QwenPaw",
    app_description="A helpful assistant with background task support",
    runner=runner,
    enable_stream_task=True,
    stream_task_queue="stream_query",
    stream_task_timeout=300,
)


@asynccontextmanager
async def lifespan(  # pylint: disable=too-many-statements,too-many-branches
    app: FastAPI,
):
    startup_start_time = time.time()
    add_project_file_handler(LOG_FILE_PATH)

    # ================================================================
    # Phase 1: Fast synchronous setup (target < 100ms)
    # Everything here must be lightweight so the server starts quickly.
    # ================================================================

    try:
        cleanup_startup_restore_artifacts()
    except Exception as exc:
        message = (
            "QwenPaw startup failed because restore artifact cleanup did not "
            "complete. Another restore or cleanup may still be running, or "
            "a previous restore may need recovery before startup can safely "
            "read restored files."
        )
        logger.error(message, exc_info=True)
        raise RuntimeError(f"{message} Original error: {exc}") from exc

    auto_register_from_env()

    # ---- 企业运行时脊柱 ----
    from ..enterprise.runtime import create_enterprise_runtime

    enterprise_runtime = create_enterprise_runtime()
    await enterprise_runtime.start()
    app.state.enterprise_runtime = enterprise_runtime

    from ..enterprise.runtime_registry import set_enterprise_runtime

    set_enterprise_runtime(enterprise_runtime)

    # 从此处到 yield 之间的任何异常都必须关闭 enterprise_runtime，
    # 因为 finally 块只在 yield 之后才生效。
    try:
        try:
            from ..utils.telemetry import (
                collect_and_upload_telemetry,
                has_telemetry_been_collected,
                is_telemetry_opted_out,
            )

            if not is_telemetry_opted_out(
                WORKING_DIR,
            ) and not has_telemetry_been_collected(WORKING_DIR):
                collect_and_upload_telemetry(WORKING_DIR)
        except Exception:
            logger.debug(
                "Telemetry collection skipped due to error",
                exc_info=True,
            )

        logger.debug("Checking for legacy config migration...")
        migrate_legacy_workspace_to_default_agent()
        ensure_default_agent_exists()
        migrate_legacy_skills_to_skill_pool()
        ensure_qa_agent_exists()

        # Create core managers (instant — no I/O)
        logger.debug("Initializing MultiAgentManager...")
        multi_agent_manager = MultiAgentManager()
        provider_manager = ProviderManager.get_instance()
        local_model_manager = LocalModelManager.get_instance()

        # Start token usage manager background tasks
        logger.debug("Starting TokenUsageManager background tasks...")
        from ..token_usage import get_token_usage_manager

        token_usage_manager = get_token_usage_manager()
        token_usage_manager.start(flush_interval=10)

        # Expose to endpoints (must be set before first request arrives)
        app.state.multi_agent_manager = multi_agent_manager
        multi_agent_manager.set_app(app)
        app.state.provider_manager = provider_manager
        app.state.local_model_manager = local_model_manager
        app.state.plugin_loader = None
        app.state.plugin_registry = None

        if isinstance(runner, DynamicMultiAgentRunner):
            runner.set_multi_agent_manager(multi_agent_manager)

        async def _get_agent_by_id(agent_id: str = None):
            """Get agent instance by ID, or active agent if not specified."""
            if agent_id is None:
                config = load_config(get_config_path())
                agent_id = config.agents.active_agent or "default"
            return await multi_agent_manager.get_agent(agent_id)

        app.state.get_agent_by_id = _get_agent_by_id

        fast_elapsed = time.time() - startup_start_time
        logger.info(
            f"Server ready in {fast_elapsed:.3f}s "
            f"(agents loading in background)",
        )

        # ================================================================
        # Phase 2: Background heavy initialization
        # Agents, plugins, and services start in a background task so the
        # server can begin accepting HTTP requests immediately.
        # First API requests that need an agent will await its readiness
        # via MultiAgentManager.get_agent() lazy-loading / event wait.
        # ================================================================

        async def _background_startup():  # pylint: disable=too-many-statements
            try:
                # Start all configured agents (truly parallel now)
                await multi_agent_manager.start_all_configured_agents()

                provider_manager.start_local_model_resume(
                    local_model_manager,
                )

                # ---- Plugin System ----
                logger.debug("Initializing plugin system...")

                from ..plugins.loader import PluginLoader
                from ..plugins.runtime import RuntimeHelpers
                from ..config.utils import get_plugins_dir

                plugin_dirs = [
                    get_plugins_dir(),
                ]

                plugin_loader = PluginLoader(plugin_dirs)

                config = load_config(get_config_path())
                plugin_configs = (
                    config.plugins if hasattr(config, "plugins") else {}
                )
                logger.debug(
                    f"Loading plugins with {len(plugin_configs)} config(s)",
                )

                loaded_plugins = await plugin_loader.load_all_plugins(
                    configs=plugin_configs,
                )
                logger.debug(f"Loaded {len(loaded_plugins)} plugin(s)")

                runtime_helpers = RuntimeHelpers(
                    provider_manager=provider_manager,
                )
                plugin_loader.registry.set_runtime_helpers(
                    runtime_helpers,
                )

                for (
                    provider_id,
                    provider_reg,
                ) in plugin_loader.registry.get_all_providers().items():
                    provider_manager.register_plugin_provider(
                        provider_id=provider_id,
                        provider_class=provider_reg.provider_class,
                        label=provider_reg.label,
                        base_url=provider_reg.base_url,
                        metadata=provider_reg.metadata,
                    )
                    logger.debug(
                        f"Registered plugin provider: {provider_id}",
                    )

                app.state.plugin_loader = plugin_loader
                app.state.plugin_registry = plugin_loader.registry

                # ---- Runtime Extension Providers ----
                # 把插件注册的 runtime extension provider 注入到
                # enterprise runtime 的 resolver，避免后台加载竞态
                _ext_resolver = getattr(
                    enterprise_runtime, "extensions", None
                )
                if _ext_resolver is not None and hasattr(
                    _ext_resolver, "register_provider"
                ):
                    _ext_providers = (
                        plugin_loader.registry.get_runtime_extension_providers()
                    )
                    for _reg in _ext_providers:
                        _ext_resolver.register_provider(_reg.provider)
                        logger.debug(
                            "Registered runtime extension provider "
                            "'%s' from plugin '%s'",
                            _reg.provider.provider_id,
                            _reg.plugin_id,
                        )

                # ---- Plugin Control Commands ----
                logger.debug(
                    "Registering plugin control commands...",
                )
                from ..app.runner.control_commands import (
                    register_command,
                )
                from ..app.channels.command_registry import (
                    CommandRegistry,
                )

                command_registry = CommandRegistry()

                control_commands = (
                    plugin_loader.registry.get_control_commands()
                )
                for cmd_reg in control_commands:
                    try:
                        register_command(cmd_reg.handler)

                        command_registry.register_command(
                            f"/{cmd_reg.handler.command_name}",
                            priority_level=cmd_reg.priority_level,
                        )

                        logger.debug(
                            f"Registered plugin control command: "
                            f"/{cmd_reg.handler.command_name} "
                            f"from plugin '{cmd_reg.plugin_id}' "
                            f"(priority={cmd_reg.priority_level})",
                        )
                    except Exception as e:
                        logger.error(
                            f"✗ Failed to register control command "
                            f"'{cmd_reg.handler.command_name}' "
                            f"from plugin '{cmd_reg.plugin_id}': "
                            f"{e}",
                            exc_info=True,
                        )

                # ---- Startup Hooks ----
                logger.debug("Executing plugin startup hooks...")
                startup_hooks = (
                    plugin_loader.registry.get_startup_hooks()
                )
                for hook in startup_hooks:
                    try:
                        logger.debug(
                            f"Executing startup hook "
                            f"'{hook.hook_name}' "
                            f"from plugin '{hook.plugin_id}' "
                            f"(priority={hook.priority})",
                        )

                        result = hook.callback()
                        if inspect.iscoroutine(
                            result,
                        ) or inspect.isawaitable(result):
                            await result

                        logger.debug(
                            f"Completed startup hook "
                            f"'{hook.hook_name}' "
                            f"from plugin '{hook.plugin_id}'",
                        )
                    except Exception as e:
                        logger.error(
                            f"✗ Failed to execute startup hook "
                            f"'{hook.hook_name}' "
                            f"from plugin '{hook.plugin_id}': "
                            f"{e}",
                            exc_info=True,
                        )

                # ---- Approval Service ----
                try:
                    default_agent = (
                        await multi_agent_manager.get_agent("default")
                    )
                    if default_agent.channel_manager:
                        from .approvals import get_approval_service

                        get_approval_service().set_channel_manager(
                            default_agent.channel_manager,
                        )
                except Exception as e:
                    logger.warning(
                        f"Approval service setup skipped: {e}",
                    )

                startup_elapsed = time.time() - startup_start_time
                logger.info(
                    "Background startup completed in "
                    f"{startup_elapsed:.3f} seconds",
                )

                # Print server URL again so it's visible
                from ..config.utils import read_last_api
                from ..utils.startup_display import (
                    print_ready_banner,
                )

                api_info = read_last_api()
                print_ready_banner(api_info, startup_elapsed)
            except Exception:
                logger.error(
                    "Background startup encountered an error",
                    exc_info=True,
                )

        _bg_task = asyncio.create_task(_background_startup())

    except Exception:
        await enterprise_runtime.stop()
        from ..enterprise.runtime_registry import clear_enterprise_runtime

        clear_enterprise_runtime(enterprise_runtime)
        raise

    try:
        yield
    finally:
        # Cancel background startup if still in progress
        if not _bg_task.done():
            _bg_task.cancel()
            with suppress(asyncio.CancelledError):
                await _bg_task

        # ==================== Execute Shutdown Hooks ====================
        plugin_registry = getattr(app.state, "plugin_registry", None)
        if plugin_registry is not None:
            logger.info("Executing plugin shutdown hooks...")
            shutdown_hooks = plugin_registry.get_shutdown_hooks()
            for hook in shutdown_hooks:
                try:
                    logger.info(
                        f"Executing shutdown hook '{hook.hook_name}' "
                        f"from plugin '{hook.plugin_id}' (priority"
                        f"={hook.priority})",
                    )

                    result = hook.callback()
                    if inspect.iscoroutine(result) or inspect.isawaitable(
                        result,
                    ):
                        await result

                    logger.info(
                        f"✓ Completed shutdown hook '{hook.hook_name}' "
                        f"from plugin '{hook.plugin_id}'",
                    )
                except Exception as e:
                    logger.error(
                        f"✗ Failed to execute shutdown hook "
                        f"'{hook.hook_name}' "
                        f"from plugin '{hook.plugin_id}': {e}",
                        exc_info=True,
                    )

        local_model_mgr = getattr(app.state, "local_model_manager", None)
        if local_model_mgr is not None:
            logger.info("Stopping local model server...")
            try:
                await local_model_mgr.shutdown_server()
            except Exception as exc:
                logger.error(
                    "Error shutting down local model server gracefully: %s",
                    exc,
                )
                with suppress(OSError, RuntimeError, ValueError):
                    local_model_mgr.shutdown_server_sync()

        # Stop multi-agent manager (stops all agents and their components)
        multi_agent_mgr = getattr(app.state, "multi_agent_manager", None)
        if multi_agent_mgr is not None:
            logger.info("Stopping MultiAgentManager...")
            try:
                await multi_agent_mgr.stop_all()
            except Exception as e:
                logger.error(f"Error stopping MultiAgentManager: {e}")

        # ---- 企业运行时关闭 ----
        _enterprise_runtime = getattr(app.state, "enterprise_runtime", None)
        if _enterprise_runtime is not None:
            logger.info("Stopping EnterpriseRuntime...")
            try:
                await _enterprise_runtime.stop()
            except Exception as e:
                logger.error(f"Error stopping EnterpriseRuntime: {e}")

        from ..enterprise.runtime_registry import clear_enterprise_runtime

        clear_enterprise_runtime(_enterprise_runtime)

        # Stop token usage manager (drain queue and final flush)
        logger.info("Stopping TokenUsageManager...")
        try:
            await token_usage_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping TokenUsageManager: {e}")

        logger.info("Application shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

# 中间件注册顺序（add_middleware 为 LIFO 栈，后加的先执行）
# 实际执行顺序：RequestIdentity → Auth → Authz → AgentContext → route

# 最先注册（最后执行）
# 执行顺序（最先→最后）：Observability → RequestIdentity → Auth → Authz → AgentContext → Quota
# Quota 最后执行，确保能拿到 AgentContext 设置的 agent_id
from ..enterprise.quota.middleware import QuotaMiddleware

app.add_middleware(QuotaMiddleware)

app.add_middleware(AgentContextMiddleware)

# 企业运行时：授权中间件（读 request.state.user / webchat_identity + 权限矩阵）
from ..enterprise.authz.middleware import AuthzMiddleware

app.add_middleware(AuthzMiddleware)

# Console 鉴权（写 request.state.user）
app.add_middleware(AuthMiddleware)

# 企业运行时：请求标识中间件（写 request_id / trace_id）
from ..enterprise.middleware import RequestIdentityMiddleware

app.add_middleware(RequestIdentityMiddleware)

# 企业运行时：可观测性中间件（记录 HTTP 指标）
from ..enterprise.observability.middleware import ObservabilityMiddleware

app.add_middleware(ObservabilityMiddleware)

# 安全中间件（LIFO 栈：后注册的先执行，包裹所有内部响应）
# 执行顺序（最先→最后）：SecurityHeaders → PayloadSize → CSRF → ... → route
# 即使 PayloadSize/CSRF 短路返回，SecurityHeaders 已经包裹响应
from ..enterprise.security.middleware import (
    CSRFMiddleware,
    PayloadSizeMiddleware,
    SecurityHeadersMiddleware,
    build_default_payload_route_limits,
    get_default_max_payload_bytes,
)

app.add_middleware(CSRFMiddleware)
app.add_middleware(
    PayloadSizeMiddleware,
    max_bytes=get_default_max_payload_bytes(),
    route_limits=build_default_payload_route_limits(),
)
app.add_middleware(SecurityHeadersMiddleware)

# Apply CORS middleware using strict options
from ..enterprise.security.cors import build_cors_options

cors_options = build_cors_options()
if cors_options["allow_origins"]:
    app.add_middleware(CORSMiddleware, **cors_options)


# ---------- 前端静态路由 ----------
from .frontend_static import (
    resolve_frontend_build,
    register_frontend_routes,
)

_CONSOLE_BUILD = resolve_frontend_build(
    name="console",
    env_var="QWENPAW_CONSOLE_STATIC_DIR",
    pkg_subdir="console",
    repo_subdir="console/dist",
    url_prefix="/console",
)
logger.info(f"CONSOLE_STATIC_DIR: {_CONSOLE_BUILD.static_dir}")

_WEBCHAT_BUILD = resolve_frontend_build(
    name="webchat",
    env_var="QWENPAW_WEBCHAT_STATIC_DIR",
    pkg_subdir="webchat",
    repo_subdir="webchat/dist",
    url_prefix="/webchat",
)
logger.info(f"WEBCHAT_STATIC_DIR: {_WEBCHAT_BUILD.static_dir}")

_ENTERPRISE_ADMIN_BUILD = resolve_frontend_build(
    name="enterprise-admin",
    env_var="QWENPAW_ENTERPRISE_ADMIN_STATIC_DIR",
    pkg_subdir="enterprise-admin",
    repo_subdir="enterprise-admin/dist",
    url_prefix="/enterprise-admin",
)
logger.info(f"ENTERPRISE_ADMIN_STATIC_DIR: {_ENTERPRISE_ADMIN_BUILD.static_dir}")


# 导入 _log_frontend_index_refs 并记录所有前端
from .frontend_static import _log_frontend_index_refs

_log_frontend_index_refs("console", _CONSOLE_BUILD.index_path)
_log_frontend_index_refs("webchat", _WEBCHAT_BUILD.index_path)
_log_frontend_index_refs("enterprise-admin", _ENTERPRISE_ADMIN_BUILD.index_path)


@app.get("/api/version")
def get_version():
    """Return the current application version (public-safe payload)."""
    return {
        "version": __version__,
    }


@app.get("/api/doctor/runtime")
def get_doctor_runtime():
    """Return server runtime diagnostics for authenticated troubleshooting."""
    return {
        "python_executable": sys.executable,
        "python_environment": summarize_python_environment(),
    }


# Health/Ready 端点（无鉴权，部署平台探测）
from ..enterprise.reliability.router import create_reliability_router

app.include_router(create_reliability_router())

# Metrics 端点（先于其他 router 注册）
from ..enterprise.observability.router import create_metrics_router

app.include_router(create_metrics_router(), prefix="/api")

from ..enterprise.compliance.router import create_compliance_router

app.include_router(create_compliance_router(), prefix="/api")

app.include_router(api_router, prefix="/api")

# Approval router: /api/approval/approve, /api/approval/deny, etc.
app.include_router(approval_router, prefix="/api")

# Agent-scoped router: /api/agents/{agentId}/chats, etc.
agent_scoped_router = create_agent_scoped_router()
app.include_router(agent_scoped_router, prefix="/api")

app.include_router(
    agent_app.router,
    prefix="/api/agent",
    tags=["agent"],
)

# Voice channel: Twilio-facing endpoints at root level (not under /api/).
# POST /voice/incoming, WS /voice/ws, POST /voice/status-callback
app.include_router(voice_router, tags=["voice"])

# Custom channel routes (before SPA catch-all to ensure route priority)
register_custom_channel_routes(app)

# 前端静态路由（console/webchat/enterprise-admin）
# 必须在 API 路由之后注册以确保优先级正确
register_frontend_routes(
    app=app,
    console_build=_CONSOLE_BUILD,
    webchat_build=_WEBCHAT_BUILD,
    enterprise_build=_ENTERPRISE_ADMIN_BUILD,
)
