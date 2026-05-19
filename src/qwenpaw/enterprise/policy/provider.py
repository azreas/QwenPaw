from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.interfaces import RuntimeExtensionBundle, ToolPolicyPatch

from .models import PolicyAction

if TYPE_CHECKING:
    from .service import PolicyService


class PolicyRuntimeExtensionProvider:
    provider_id = "policy-kernel"

    def __init__(
        self,
        policy: "PolicyService",
        *,
        tool_resources: Iterable[str] = (),
    ) -> None:
        self._policy = policy
        self._tool_resources = tuple(tool_resources)

    async def resolve(self, ctx: RequestContext) -> RuntimeExtensionBundle:
        denied_tools: list[str] = []
        for tool_name in self._tool_resources:
            decision = await self._policy.evaluate(
                ctx,
                PolicyAction.TOOL_CALL,
                tool_name,
            )
            if not decision.allowed:
                denied_tools.append(tool_name)

        return RuntimeExtensionBundle(
            tool_policy=ToolPolicyPatch(
                disable_tools=frozenset(denied_tools),
                deny_tools=frozenset(denied_tools),
            ),
            metadata={"policy": {"denied_tools": denied_tools}},
        )
