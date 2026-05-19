from dataclasses import dataclass

from qwenpaw.app.webchat.session import WebchatIdentity


@dataclass(frozen=True)
class EnterpriseIdentityCase:
    employee_id: str
    tenant_id: str
    name: str = "测试员工"

    def webchat_identity(self) -> WebchatIdentity:
        return WebchatIdentity.from_sso(
            employee_id=self.employee_id,
            wechat_company_id=self.tenant_id,
            full_name=self.name,
        )


ZHANGSAN = EnterpriseIdentityCase(
    employee_id="emp_zhangsan",
    tenant_id="zhangsan",
)
LISI = EnterpriseIdentityCase(
    employee_id="emp_lisi",
    tenant_id="lisi",
)
