# -*- coding: utf-8 -*-
from __future__ import annotations

_IDENTITY_FIELD_LABELS = {
    "fullName/realName": "姓名(fullName/realName)",
    "employeeId": "工号(employeeId)",
    "wechatCompanyId": "企微 ID(wechatCompanyId)",
}


def build_missing_identity_fields_detail(missing: list[str]) -> str:
    fields = [_IDENTITY_FIELD_LABELS.get(field, field) for field in missing]
    return f"登录服务返回身份信息缺少：{'、'.join(fields)}"
