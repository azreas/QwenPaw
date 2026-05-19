import pytest

from qwenpaw.plugins.sandbox_runtime.contract import (
    SandboxContractError,
    assert_sandbox_client_contract,
    get_sandbox_client_contract,
)


class FakeClient:
    def __init__(self, tools=None):
        self._tools = tools or [{"name": "sandbox_shell"}]
        self._qwenpaw_rebuild_info = {
            "transport": "streamable_http",
            "name": "sandbox-wx_acme",
            "url": "http://gw",
            "headers": {
                "X-Tenant-Id": "wx_acme",
                "X-Agent-Id": "wx_acme",
                "X-Session-Id": "s1",
            },
        }

    async def list_tools(self):
        return self._tools


@pytest.mark.asyncio
async def test_contract_accepts_client_with_metadata_and_tools():
    contract = await assert_sandbox_client_contract(
        FakeClient(),
        expected_tenant_id="wx_acme",
        require_list_tools=True,
    )

    assert contract["name"] == "sandbox-wx_acme"
    assert contract["tool_count"] == 1


@pytest.mark.asyncio
async def test_contract_rejects_missing_tenant_header():
    client = FakeClient()
    client._qwenpaw_rebuild_info["headers"]["X-Tenant-Id"] = ""

    with pytest.raises(SandboxContractError, match="X-Tenant-Id"):
        await assert_sandbox_client_contract(
            client,
            expected_tenant_id="wx_acme",
            require_list_tools=False,
        )


def test_get_contract_reads_rebuild_info():
    contract = get_sandbox_client_contract(FakeClient())
    assert contract["transport"] == "streamable_http"
    assert contract["url"] == "http://gw"
