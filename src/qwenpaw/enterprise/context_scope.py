"""Context managers for enterprise request-scoped runtime state."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .context import (
    RequestContext,
    clear_current_request_context,
    clear_current_tool_policy_patch,
    set_current_request_context,
    set_current_tool_policy_patch,
)


@contextmanager
def enterprise_context_scope(
    ctx: RequestContext,
    tool_policy_patch: Any | None = None,
) -> Iterator[None]:
    request_token = set_current_request_context(ctx)
    policy_token = set_current_tool_policy_patch(tool_policy_patch)
    try:
        yield
    finally:
        clear_current_tool_policy_patch(policy_token)
        clear_current_request_context(request_token)
