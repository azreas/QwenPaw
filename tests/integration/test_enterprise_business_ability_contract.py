from fastapi.testclient import TestClient

from tests.fixtures.mock_mcp_server import app


def test_mock_mcp_success_contract():
    """验证 MCP 成功响应契约字段：status, ability_type, ability_name, answer"""
    response = TestClient(app).post(
        "/tools/sales_metric",
        json={"question": "查询销售额"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["ability_type"] == "mcp"
    assert data["ability_name"] == "sales_metric"
    assert data["answer"] == "样例指标结果"


def test_mock_mcp_failure_contract():
    """验证 MCP 失败响应契约字段：status, error_reason"""
    response = TestClient(app).post(
        "/tools/sales_metric",
        json={"question": "触发失败"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failure"
    assert data["error_reason"] == "mock business failure"
