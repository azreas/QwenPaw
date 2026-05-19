from qwenpaw.tenancy.ids import tenant_agent_id
from tests.fixtures.enterprise_identity import LISI, ZHANGSAN


def test_webchat_and_wecom_identity_share_agent_id():
    """验证身份契约：SSO 中的 wechat_company_id 与企微回调的 from.userid
    必须一致，且收敛到同一个 wx_* 工作区。
    """
    identity = ZHANGSAN.webchat_identity()
    wecom_userid = ZHANGSAN.tenant_id

    assert identity.tenant_id == wecom_userid
    assert identity.agent_id == tenant_agent_id(wecom_userid)
    assert identity.agent_id.startswith("wx_")


def test_two_employees_resolve_to_different_tenant_workspaces():
    """验证多租户隔离：不同员工应该解析到不同的工作区。"""
    zhangsan = ZHANGSAN.webchat_identity()
    lisi = LISI.webchat_identity()

    assert zhangsan.tenant_id != lisi.tenant_id
    assert zhangsan.agent_id != lisi.agent_id
