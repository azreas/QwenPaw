# -*- coding: utf-8 -*-
"""验证 ReMeLightMemoryManager 支持预加载 agent_config，不依赖静态 load_agent_config。"""
from unittest.mock import patch

import pytest

from qwenpaw.config.config import (
    AgentProfileConfig,
    AgentsRunningConfig,
    ReMeLightMemoryConfig,
)


@pytest.fixture
def tenant_agent_config(tmp_path):
    """构建不存在的动态租户配置（不在静态 profiles 内）。"""
    running = AgentsRunningConfig(
        reme_light_memory_config=ReMeLightMemoryConfig(),
    )
    return AgentProfileConfig(
        id="wx_dynamic_tenant",
        name="wx_dynamic_tenant",
        workspace_dir=str(tmp_path),
        running=running,
    )


def test_memory_manager_uses_preloaded_config_not_static_lookup(
    tmp_path, tenant_agent_config,
):
    """传入 agent_config 时不应触发 load_agent_config() 查找静态 profiles。"""
    from qwenpaw.agents.memory.reme_light_memory_manager import (
        ReMeLightMemoryManager,
    )

    # 关键：load_agent_config 被 mock 为直接抛错，若代码走静态查找路径则测试失败
    with patch(
        "qwenpaw.agents.memory.reme_light_memory_manager.load_agent_config",
        side_effect=RuntimeError("不得调用静态 load_agent_config"),
    ), patch(
        "reme.reme_light.ReMeLight",
    ), patch.object(
        ReMeLightMemoryManager,
        "_check_reme_version",
        return_value=True,
    ):
        mm = ReMeLightMemoryManager(
            working_dir=str(tmp_path),
            agent_id="wx_dynamic_tenant",
            agent_config=tenant_agent_config,
        )
        assert mm is not None
