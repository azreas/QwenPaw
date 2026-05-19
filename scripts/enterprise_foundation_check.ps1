$ErrorActionPreference = "Stop"

$commands = @(
    ".venv\Scripts\python.exe -m pytest tests/unit/app/webchat tests/unit/channels/test_wecom_tenant_channel.py tests/unit/tenancy tests/unit/routers/test_wecom_tenant_config.py tests/unit/routers/test_wecom_tenant_ops.py tests/unit/enterprise tests/unit/backup tests/integration/test_app_startup.py tests/integration/test_enterprise_identity_contract.py tests/integration/test_enterprise_business_ability_contract.py -q --basetemp .tmp\pytest-enterprise-foundation",
    ".venv\Scripts\python.exe -m compileall src/qwenpaw",
    "npm.cmd --prefix console run test -- --run",
    "npm.cmd --prefix console run build",
    "npm.cmd --prefix webchat run build",
    "git diff --check"
)

foreach ($command in $commands) {
    Write-Host ">>> $command"
    Invoke-Expression $command
}
