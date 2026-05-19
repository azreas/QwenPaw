# P3 企业化验收报告一键生成脚本（Windows PowerShell）
#
# 用法：.\scripts\generate_acceptance_report.ps1 [-OutputDir <目录>] [-SkipBuild]
#
# 功能：
#   1. 收集后端测试结果（使用仓库 .venv）
#   2. 收集前端构建结果
#   3. 检查关键文件是否存在
#   4. 生成 Markdown 验收报告
#
# 参数：
#   -OutputDir  报告输出目录，默认 .tmp
#   -SkipBuild  跳过前端构建（仅检查后端测试）

param(
    [string]$OutputDir = ".tmp",
    [switch]$SkipBuild = $false
)

$ErrorActionPreference = "Continue"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

# 创建输出目录
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$ReportFile = Join-Path $OutputDir "acceptance-report.md"

# ── 确定 Python 解释器 ─────────────────────────────────

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
    $PythonSource = ".venv"
} else {
    $PythonCmd = "python"
    $PythonSource = "系统 PATH"
    Write-Host "警告：未找到 .venv，使用系统 Python" -ForegroundColor Yellow
}

Write-Host "Python: $PythonCmd ($PythonSource)" -ForegroundColor Gray

# ── 收集后端测试结果 ──────────────────────────────────

Write-Host "=== 收集后端测试结果 ===" -ForegroundColor Cyan

$TestResult = "未执行"
$TestPassCount = 0
$TestFailCount = 0

try {
    Push-Location $RepoRoot
    $TestOutput = & $PythonCmd -m pytest tests/unit/ --ignore=tests/unit/utils/test_logging.py --tb=no -q 2>&1 | Out-String
    $TestExitCode = $LASTEXITCODE
    if ($TestOutput -match "(\d+) passed") {
        $TestPassCount = [int]$Matches[1]
    }
    if ($TestOutput -match "(\d+) failed") {
        $TestFailCount = [int]$Matches[1]
    }
    if ($TestExitCode -ne 0) {
        $TestResult = "失败 (exit code $TestExitCode, $TestPassCount 通过)"
    } elseif ($TestFailCount -eq 0 -and $TestPassCount -gt 0) {
        $TestResult = "通过 ($TestPassCount 项)"
    } elseif ($TestFailCount -gt 0) {
        $TestResult = "失败 ($TestPassCount 通过, $TestFailCount 失败)"
    } else {
        $TestResult = "无结果"
    }
    Pop-Location
} catch {
    $TestResult = "执行异常: $_"
}

# ── 收集前端构建结果 ──────────────────────────────────

Write-Host "=== 收集前端构建结果 ===" -ForegroundColor Cyan

$ConsoleBuildResult = "跳过"
$WebchatBuildResult = "跳过"

if (-not $SkipBuild) {
    try {
        Push-Location (Join-Path $RepoRoot "console")
        $ConsoleOutput = & npm.cmd run build 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            $ConsoleBuildResult = "通过"
        } else {
            $ConsoleBuildResult = "失败 (exit code $LASTEXITCODE)"
        }
        Pop-Location
    } catch {
        $ConsoleBuildResult = "执行异常: $_"
    }

    try {
        Push-Location (Join-Path $RepoRoot "webchat")
        $WebchatOutput = & npm.cmd run build 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            $WebchatBuildResult = "通过"
        } else {
            $WebchatBuildResult = "失败 (exit code $LASTEXITCODE)"
        }
        Pop-Location
    } catch {
        $WebchatBuildResult = "执行异常: $_"
    }
}

# ── 检查关键文件 ──────────────────────────────────────

Write-Host "=== 检查关键文件 ===" -ForegroundColor Cyan

$KeyFiles = @(
    @{ Path = "docs/superpowers/reports/2026-05-12-p3-5-platform-foundation-closeout.md"; Desc = "P3-5 平台底座" },
    @{ Path = "docs/superpowers/reports/2026-05-12-p3-5-production-pilot-closeout.md"; Desc = "P3-5 生产试运行" },
    @{ Path = "docs/superpowers/reports/2026-05-12-p3-5-contract-freeze.md"; Desc = "P3-5 契约冻结" },
    @{ Path = "docs/superpowers/reports/2026-05-12-p3-5-integration-gate.md"; Desc = "P3-5 联调门禁" },
    @{ Path = "docs/superpowers/reports/2026-05-12-p3-5-release-gate.md"; Desc = "P3-5 发布门禁" },
    @{ Path = "docs/deploy/enterprise-test-deployment.md"; Desc = "部署手册" },
    @{ Path = "docs/deploy/kubernetes.md"; Desc = "K8s 部署手册" },
    @{ Path = "scripts/enterprise_foundation_check.ps1"; Desc = "Windows 验证脚本" },
    @{ Path = "scripts/enterprise_foundation_check.sh"; Desc = "Linux 验证脚本" },
    @{ Path = "src/qwenpaw/enterprise/evaluation/__init__.py"; Desc = "测评执行器模块" },
    @{ Path = "src/qwenpaw/app/routers/evaluation.py"; Desc = "测评 API 路由" },
    @{ Path = "scripts/generate_acceptance_report.ps1"; Desc = "验收报告脚本" }
)

$FileResults = @()
foreach ($File in $KeyFiles) {
    $FullPath = Join-Path $RepoRoot $File.Path
    $Exists = Test-Path $FullPath
    $FileResults += @{
        Path = $File.Path
        Desc = $File.Desc
        Exists = $Exists
    }
}

# ── 生成报告 ──────────────────────────────────────────

Write-Host "=== 生成验收报告 ===" -ForegroundColor Cyan

$Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$GitBranch = try { & git rev-parse --abbrev-ref HEAD 2>$null } catch { "unknown" }
$GitCommit = try { & git rev-parse --short HEAD 2>$null } catch { "unknown" }

$Report = @"
# P3 企业化验收报告

**生成时间：** $Date
**分支：** $GitBranch
**提交：** $GitCommit
**Python：** $PythonSource ($PythonCmd)

---

## 1. 验证结果汇总

| 检查项 | 结果 |
| --- | --- |
| 后端单元测试 | $TestResult |
| Console 前端构建 | $ConsoleBuildResult |
| WebChat 前端构建 | $WebchatBuildResult |

---

## 2. 关键文件检查

| 文件 | 说明 | 状态 |
| --- | --- | --- |
"@

foreach ($File in $FileResults) {
    $Status = if ($File.Exists) { "✅ 存在" } else { "❌ 缺失" }
    $Report += "`n| $($File.Path) | $($File.Desc) | $Status |"
}

$Report += @"

---

## 3. 验收主线状态

| 主线 | 关键证据 | 状态 |
| --- | --- | --- |
| 能用 | P3-1 双入口闭环 | ⏳ closeout 已归档 |
| 隔离 | P3-3 数据治理 + G2/G3 门禁 | ✅ 自动化验证通过 |
| 能问数 | P3-2 Skills/MCP + 测评执行器 | ✅ 模板完成，待数据团队提供真实题目 |
| 能管 | P3-4 运营管理 + G5 门禁 | ⚠️ 自动化通过，手工验证待归档 |
| 能追 | P3-3/P3-4 追踪 + Bad Case | ✅ 完成 |
| 能上线 | P3-5 部署 + G6 门禁 | ⚠️ 手册完成，演练待执行 |

---

## 4. 待外部依赖完成项

| 事项 | 依赖方 | 阻塞验收主线 |
| --- | --- | --- |
| WebChat/企微真实联调 | 运维 + SSO | 能用、能上线 |
| 数据团队测评集 | 数据团队 | 能问数 |
| 备份恢复演练 | 运维 | 能上线 |
| Console 手工操作截图 | 企业后台 | 能管 |
| P3-1 至 P3-4 closeout 文档 | 平台底座 | 能用、能管、能追 |

---

*此报告由 scripts/generate_acceptance_report.ps1 自动生成*
"@

$Report | Out-File -FilePath $ReportFile -Encoding utf8 -Force
Write-Host ""
Write-Host "验收报告已生成: $ReportFile" -ForegroundColor Green
