# -*- coding: utf-8 -*-
"""租户 ID 与动态 agent ID 归一化。"""
from __future__ import annotations

import hashlib
import re

_PATH_INJECTION_RE = re.compile(r'[/\\<>:"|?*\x00-\x1f]|\.\.')


def safe_tenant_suffix(tenant_id: str) -> str:
    """返回可用于目录名和 agent_id 后缀的安全租户标识。"""
    value = str(tenant_id or "").strip()
    if not value:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    if _PATH_INJECTION_RE.search(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return value


def tenant_agent_id(tenant_id: str) -> str:
    """返回企业微信租户对应的动态 agent_id。"""
    return f"wx_{safe_tenant_suffix(tenant_id)}"
