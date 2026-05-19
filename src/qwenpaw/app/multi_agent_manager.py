# -*- coding: utf-8 -*-
"""MultiAgentManager: Manages multiple agent workspaces with lazy loading.

Provides centralized management for multiple Workspace objects,
including lazy loading, lifecycle management, and hot reloading.
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Set

from agentscope_runtime.engine.schemas.exception import (
    ConfigurationException,
)

from .agent_resolver import AgentResolver, ResolvedAgentRef
from .workspace import Workspace
from ..config.utils import load_config

logger = logging.getLogger(__name__)


class MultiAgentManager:
    """Manages multiple agent workspaces.

    Features:
    - Lazy loading: Workspaces are created only when first requested
    - Lifecycle management: Start, stop, reload workspaces
    - Thread-safe: Uses async lock for concurrent access
    - Hot reload: Reload individual workspaces without affecting others
    - Parallel startup: Multiple agents start concurrently via
      fine-grained locking (lock released during slow workspace init)
    """

    def __init__(self):
        """Initialize multi-agent manager."""
        self.agents: Dict[str, Workspace] = {}
        self._agent_refs: Dict[str, ResolvedAgentRef] = {}
        self._lock = asyncio.Lock()
        self._pending_starts: Dict[str, asyncio.Event] = {}
        self._cleanup_tasks: Set[asyncio.Task] = set()
        self._app = None  # Starlette app reference for enterprise storage
        logger.debug("MultiAgentManager initialized")

    def set_app(self, app: object) -> None:
        """Set Starlette app reference for enterprise storage access.

        Args:
            app: Starlette app instance
        """
        self._app = app

    def _resolve_agent_ref(self, agent_id: str) -> ResolvedAgentRef | None:
        """Resolve static or dynamic agent reference."""
        return AgentResolver().resolve(agent_id)

    @staticmethod
    def _create_workspace_from_ref(ref: ResolvedAgentRef) -> Workspace:
        kwargs = {
            "agent_id": ref.agent_id,
            "workspace_dir": ref.workspace_dir,
        }
        if ref.agent_config is not None:
            kwargs["agent_config"] = ref.agent_config
        return Workspace(**kwargs)

    async def get_agent(self, agent_id: str) -> Workspace:
        """Get agent workspace by ID (lazy loading with dedup).

        If workspace doesn't exist in memory, it will be created and started.
        Multiple concurrent callers for the same agent_id are coordinated:
        the first caller creates the workspace while others wait.

        The lock is only held briefly for dict checks/mutations, not during
        the slow workspace startup, allowing parallel agent initialization.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            Workspace: The requested workspace instance

        Raises:
            ConfigurationException: If agent ID not found in configuration
        """
        requested_agent_id = str(agent_id or "").strip()

        # Fast path: already loaded (no lock)
        if requested_agent_id in self.agents:
            logger.debug(f"Returning cached agent: {requested_agent_id}")
            return self.agents[requested_agent_id]

        should_start = False
        event = None
        agent_ref = None
        agent_id = requested_agent_id

        async with self._lock:
            # Re-check under lock
            if requested_agent_id in self.agents:
                logger.debug(f"Returning cached agent: {requested_agent_id}")
                return self.agents[requested_agent_id]

            # Validate config and switch to the canonical id returned by
            # the resolver before touching pending/cache state.
            agent_ref = self._resolve_agent_ref(requested_agent_id)
            if agent_ref is None:
                raise ConfigurationException(
                    config_key="agent",
                    message=(
                        f"Agent '{requested_agent_id}' not found "
                        f"in configuration"
                    ),
                )
            if not agent_ref.enabled:
                raise ConfigurationException(
                    config_key="agent",
                    message=f"Agent '{requested_agent_id}' is disabled",
                )

            agent_id = agent_ref.agent_id
            if agent_id in self.agents:
                logger.debug(f"Returning cached agent: {agent_id}")
                return self.agents[agent_id]

            if agent_id in self._pending_starts:
                # Another task is already starting this agent; wait for it
                event = self._pending_starts[agent_id]
            else:
                event = asyncio.Event()
                self._pending_starts[agent_id] = event
                should_start = True

        if not should_start:
            # Wait for the in-progress startup to finish
            await event.wait()
            if agent_id in self.agents:
                logger.debug(f"Returning cached agent: {agent_id}")
                return self.agents[agent_id]
            raise ConfigurationException(
                config_key="agent",
                message=f"Agent '{agent_id}' failed to initialize",
            )

        # We are the starter — create outside the lock for parallelism
        t0 = time.perf_counter()
        logger.debug(f"Creating new workspace: {agent_id}")
        assert agent_ref is not None  # guarded by should_start branch above

        try:
            instance = self._create_workspace_from_ref(agent_ref)
            instance.set_manager(self)
            await instance.start()

            async with self._lock:
                self.agents[agent_id] = instance
                self._agent_refs[agent_id] = agent_ref

            elapsed = time.perf_counter() - t0
            logger.debug(
                f"Workspace created and started: {agent_id} "
                f"({elapsed:.3f}s)",
            )
            return instance
        except Exception as e:
            logger.error(f"Failed to start workspace {agent_id}: {e}")
            raise
        finally:
            # Always clean up pending state and signal waiters
            # This handles cancellation (CancelledError) and all other cases
            async with self._lock:
                self._pending_starts.pop(agent_id, None)
            event.set()

    async def get_or_create_tenant_agent(
        self,
        agent_id: str,
        workspace_dir: str | Path,
    ) -> Workspace:
        """Get or start a dynamic tenant workspace outside static profiles."""
        agent_id = str(agent_id or "").strip()

        if agent_id in self.agents:
            logger.debug(f"Returning cached tenant agent: {agent_id}")
            return self.agents[agent_id]

        should_start = False
        event = None

        async with self._lock:
            if agent_id in self.agents:
                logger.debug(f"Returning cached tenant agent: {agent_id}")
                return self.agents[agent_id]

            if agent_id in self._pending_starts:
                event = self._pending_starts[agent_id]
            else:
                event = asyncio.Event()
                self._pending_starts[agent_id] = event
                should_start = True

        if not should_start:
            await event.wait()
            if agent_id in self.agents:
                logger.debug(f"Returning cached tenant agent: {agent_id}")
                return self.agents[agent_id]
            raise ConfigurationException(
                config_key="agent",
                message=f"Tenant agent '{agent_id}' failed to initialize",
            )

        from qwenpaw.tenancy.tenant_agent_config import load_tenant_agent_config

        try:
            resolved_workspace_dir = Path(workspace_dir).expanduser()
            tenant_config = load_tenant_agent_config(
                resolved_workspace_dir,
                fallback_agent_id=agent_id,
            )
            instance = Workspace(
                agent_id=agent_id,
                workspace_dir=resolved_workspace_dir,
                agent_config=tenant_config,
            )
            instance.set_manager(self)
            await instance.start()

            # P3-2: 将企业运行时注入到 tenant workspace runner，
            # 使 mcp:call / skills:call 权限检查和业务追踪在生产路径生效。
            if self._app is not None:
                _er = getattr(self._app.state, "enterprise_runtime", None)
                if _er is not None and instance.runner is not None:
                    instance.runner._enterprise_runtime = _er
                    logger.debug(
                        "Injected enterprise_runtime into runner for %s",
                        agent_id,
                    )

            async with self._lock:
                self.agents[agent_id] = instance
                self._agent_refs[agent_id] = ResolvedAgentRef(
                    agent_id=agent_id,
                    workspace_dir=resolved_workspace_dir,
                    agent_config=tenant_config,
                    source="tenant_workspace",
                    enabled=True,
                )

            logger.info("Tenant workspace started: %s", agent_id)
            return instance
        except Exception as e:
            logger.error("Failed to start tenant workspace %s: %s", agent_id, e)
            raise
        finally:
            async with self._lock:
                self._pending_starts.pop(agent_id, None)
            event.set()

    async def _graceful_stop_old_instance(
        self,
        old_instance: Workspace,
        agent_id: str,
    ) -> None:
        """Gracefully stop old instance after checking for active tasks.

        If active tasks exist, schedule delayed cleanup in background.
        Otherwise, stop immediately.

        Args:
            old_instance: The old workspace instance to stop
            agent_id: Agent ID for logging
        """
        has_active = await old_instance.task_tracker.has_active_tasks()

        if has_active:
            # Active tasks - schedule delayed cleanup in background
            active_tasks = await old_instance.task_tracker.list_active_tasks()
            logger.info(
                f"Old workspace instance has {len(active_tasks)} active "
                f"task(s): {active_tasks}. Scheduling delayed cleanup for "
                f"{agent_id}.",
            )

            async def delayed_cleanup():
                """Wait for tasks to complete, then stop old instance."""
                try:
                    # Wait up to 1 minutes for tasks to complete
                    completed = await old_instance.task_tracker.wait_all_done(
                        timeout=60.0,
                    )
                    if completed:
                        logger.info(
                            f"All tasks completed for old instance "
                            f"{agent_id}. Stopping now.",
                        )
                    else:
                        logger.warning(
                            f"Timeout waiting for tasks to complete for "
                            f"{agent_id}. Forcing stop after 5 minutes.",
                        )

                    await old_instance.stop(final=False)
                    logger.info(
                        f"Old workspace instance stopped: {agent_id}. "
                        f"Delayed cleanup completed.",
                    )
                except Exception as e:
                    logger.warning(
                        f"Error during delayed cleanup for {agent_id}: {e}. "
                        f"New instance is serving requests.",
                    )

            # Create background task for delayed cleanup and track it
            cleanup_task = asyncio.create_task(delayed_cleanup())
            self._cleanup_tasks.add(cleanup_task)

            def _on_cleanup_done(task: asyncio.Task) -> None:
                """Remove task from tracking set and log errors."""
                self._cleanup_tasks.discard(task)
                if task.cancelled():
                    logger.info(
                        f"Delayed cleanup task for {agent_id} was cancelled.",
                    )
                    return
                exc = task.exception()
                if exc is not None:
                    logger.warning(
                        f"Error in delayed cleanup task for {agent_id}: "
                        f"{exc}.",
                    )

            cleanup_task.add_done_callback(_on_cleanup_done)
            logger.info(
                f"Zero-downtime reload completed: {agent_id}. "
                f"Old instance cleanup scheduled in background.",
            )
        else:
            # No active tasks - stop immediately
            logger.debug(
                f"No active tasks in old instance {agent_id}. "
                f"Stopping immediately.",
            )
            try:
                await old_instance.stop(final=False)
                logger.info(
                    f"Old workspace instance stopped: {agent_id}. "
                    f"Zero-downtime reload completed.",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to stop old workspace instance for "
                    f"{agent_id}: {e}. "
                    f"New instance is active and serving requests.",
                )

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent instance.

        Args:
            agent_id: Agent ID to stop

        Returns:
            bool: True if agent was stopped, False if not running
        """
        agent_id = str(agent_id or "").strip()

        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Agent not running: {agent_id}")
                return False

            instance = self.agents[agent_id]
            await instance.stop()
            del self.agents[agent_id]
            self._agent_refs.pop(agent_id, None)
            logger.info(f"Agent stopped and removed: {agent_id}")
            return True

    async def reload_agent(self, agent_id: str) -> bool:
        """Reload a specific agent instance with zero-downtime.

        This method performs a seamless reload by:
        1. Creating and fully starting a new workspace instance (no lock)
        2. Atomically replacing the old instance with the new one (with lock)
        3. Gracefully stopping the old instance (no lock):
           - If active tasks exist: schedule delayed cleanup in background
           - If no active tasks: stop immediately

        The lock is only held during the atomic swap to minimize blocking
        time for other agent operations.

        This ensures that:
        - New requests are immediately handled by the new instance
        - Ongoing SSE/streaming tasks continue uninterrupted
        - Other agents remain accessible during reload
        - The manager returns quickly without waiting for old tasks
        - Old instance is automatically cleaned up after tasks complete

        Args:
            agent_id: Agent ID to reload

        Returns:
            bool: True if agent was reloaded, False if not running
        """
        agent_id = str(agent_id or "").strip()

        # Step 1: Check if agent exists (quick check with lock)
        async with self._lock:
            if agent_id not in self.agents:
                logger.debug(
                    f"Agent not running, will be loaded on next "
                    f"request: {agent_id}",
                )
                return False
            old_instance = self.agents[agent_id]

        logger.info(f"Reloading agent (zero-downtime): {agent_id}")

        # Step 1.5: Stop old config watcher (no-op if it triggered
        # this reload, since it already disabled itself).
        try:
            # pylint: disable=protected-access
            old_watcher = old_instance._service_manager.services.get(
                "agent_config_watcher",
            )
            # pylint: enable=protected-access
            if old_watcher is not None:
                await old_watcher.stop()
        except Exception as stop_err:
            logger.warning(
                f"Failed to stop old AgentConfigWatcher for "
                f"{agent_id}: {stop_err}.",
            )

        # Step 2: Resolve static/dynamic reference (outside lock)
        agent_ref = self._resolve_agent_ref(agent_id)
        if agent_ref is None:
            logger.error(
                f"Agent '{agent_id}' not found in configuration "
                f"during reload",
            )
            return False

        if not agent_ref.enabled:
            logger.error(
                f"Agent '{agent_id}' is disabled during reload",
            )
            return False

        # Step 3: Create and start new workspace instance (outside lock)
        # This is the slow part, but doesn't block other agents
        logger.info(f"Creating new workspace instance: {agent_id}")
        new_instance = None

        try:
            new_instance = self._create_workspace_from_ref(agent_ref)

            # Step 3.5: Set reusable components from old instance (if any)
            async with self._lock:
                old_instance = self.agents.get(agent_id)

            if old_instance:
                # Get all reusable services from old instance's ServiceManager
                # pylint: disable=protected-access
                reusable = old_instance._service_manager.get_reusable_services()
                # pylint: enable=protected-access

                if reusable:
                    await new_instance.set_reusable_components(reusable)
                    logger.info(
                        f"Set reusable components for {agent_id}: "
                        f"{list(reusable.keys())}",
                    )

            new_instance.set_manager(self)
            await new_instance.start()
            logger.info(f"New workspace instance started: {agent_id}")
        except Exception as e:
            logger.exception(
                f"Failed to start new workspace instance for {agent_id}: {e}",
            )
            # Try to clean up the failed new instance
            if new_instance is not None:
                try:
                    await new_instance.stop()
                except Exception:
                    pass  # Best effort cleanup
            # Old instance is still running and serving requests
            return False

        # Step 4: Atomic swap (minimal lock time)
        # From this point, reload is considered successful
        async with self._lock:
            # Double-check agent still exists
            if agent_id not in self.agents:
                logger.warning(
                    f"Agent {agent_id} was removed during reload, "
                    f"stopping new instance",
                )
                await new_instance.stop()
                return False

            # Swap instances atomically
            old_instance = self.agents[agent_id]
            self.agents[agent_id] = new_instance
            self._agent_refs[agent_id] = agent_ref
            logger.info(f"Workspace instance replaced: {agent_id}")

        # Step 5: Gracefully stop old instance (outside lock)
        # Delegates to helper method to avoid too-many-statements
        await self._graceful_stop_old_instance(old_instance, agent_id)

        return True

    async def cancel_all_cleanup_tasks(self) -> None:
        """Cancel and await all pending delayed cleanup tasks.

        This ensures that any in-progress background cleanups are either
        completed or cleanly cancelled before the manager is torn down.
        Called by stop_all() during shutdown.
        """
        if not self._cleanup_tasks:
            return

        logger.info(
            f"Cancelling {len(self._cleanup_tasks)} pending cleanup "
            f"task(s)...",
        )
        tasks = list(self._cleanup_tasks)
        self._cleanup_tasks.clear()

        for task in tasks:
            if not task.done():
                task.cancel()

        # Await completion of all tasks, collecting exceptions
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All cleanup tasks cancelled/completed")

    async def stop_all(self):
        """Stop all agent instances.

        Called during application shutdown to clean up resources.
        Cancels any pending delayed cleanup tasks and stops all agents.
        """
        logger.info(f"Stopping all agents ({len(self.agents)} running)...")

        # First, cancel pending cleanup tasks to avoid orphaned instances
        await self.cancel_all_cleanup_tasks()

        # Create list of agent IDs to avoid modifying dict during iteration
        agent_ids = list(self.agents.keys())

        for agent_id in agent_ids:
            try:
                instance = self.agents[agent_id]
                await instance.stop()
                logger.debug(f"Agent stopped: {agent_id}")
            except Exception as e:
                logger.error(f"Error stopping agent {agent_id}: {e}")

        self.agents.clear()
        self._agent_refs.clear()
        logger.info("All agents stopped")

    def list_loaded_agents(self) -> list[str]:
        """List currently loaded agent IDs.

        Returns:
            list[str]: List of loaded agent IDs
        """
        return list(self.agents.keys())

    def is_agent_loaded(self, agent_id: str) -> bool:
        """Check if agent is currently loaded.

        Args:
            agent_id: Agent ID to check

        Returns:
            bool: True if agent is loaded and running
        """
        return agent_id in self.agents

    async def preload_agent(self, agent_id: str) -> bool:
        """Preload an agent instance during startup.

        Args:
            agent_id: Agent ID to preload

        Returns:
            bool: True if successfully preloaded, False if failed
        """
        try:
            await self.get_agent(agent_id)
            logger.info(f"Successfully preloaded agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to preload agent {agent_id}: {e}")
            return False

    async def start_all_configured_agents(self) -> dict[str, bool]:
        """Start all enabled agents defined in configuration concurrently.

        Only agents with enabled=True will be started.
        Disabled agents are skipped to save resources.

        Agents are started truly in parallel: get_agent() only holds the
        manager lock briefly for dict checks, releasing it during the slow
        workspace initialization.

        Returns:
            dict[str, bool]: Mapping of agent_id to success status
        """
        config = load_config()
        # Filter only enabled agents
        enabled_agents = {
            agent_id: ref
            for agent_id, ref in config.agents.profiles.items()
            if getattr(ref, "enabled", True)
        }
        agent_ids = list(enabled_agents.keys())

        if not agent_ids:
            logger.warning("No enabled agents configured in config")
            return {}

        total_agents = len(config.agents.profiles)
        disabled_count = total_agents - len(agent_ids)
        logger.debug(
            f"Starting {len(agent_ids)} enabled agent(s) "
            f"({disabled_count} disabled)",
        )

        async def start_single_agent(agent_id: str) -> tuple[str, bool]:
            """Start a single agent with error handling."""
            try:
                logger.debug(f"Starting agent: {agent_id}")
                await self.get_agent(agent_id)
                logger.debug(f"Agent started successfully: {agent_id}")
                return (agent_id, True)
            except Exception as e:
                logger.error(
                    f"Failed to start agent {agent_id}: {e}. "
                    f"Continuing with other agents...",
                )
                return (agent_id, False)

        # Truly parallel: get_agent releases lock during workspace startup
        results = await asyncio.gather(
            *[start_single_agent(agent_id) for agent_id in agent_ids],
            return_exceptions=False,
        )

        # Build result mapping
        result_map = dict(results)
        success_count = sum(1 for success in result_map.values() if success)
        logger.info(
            f"Agent startup complete: {success_count}/{len(agent_ids)} "
            f"agents started successfully, {disabled_count} disabled",
        )

        return result_map

    def __repr__(self) -> str:
        """String representation of manager."""
        loaded = list(self.agents.keys())
        return f"MultiAgentManager(loaded_agents={loaded})"
