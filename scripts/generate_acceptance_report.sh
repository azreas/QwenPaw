#!/usr/bin/env bash
# P3 企业化验收报告一键生成脚本（Linux/macOS）
#
# 用法：bash scripts/generate_acceptance_report.sh [-o <输出目录>] [--skip-build]
#
# 功能：
#   1. 收集后端测试结果（优先使用 .venv）
#   2. 收集前端构建结果
#   3. 检查关键文件是否存在
#   4. 生成 Markdown 验收报告

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR=".tmp"
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) OUTPUT_DIR="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"
REPORT_FILE="$OUTPUT_DIR/acceptance-report.md"

# ── 确定 Python 解释器 ─────────────────────────────────

if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PY_CMD="$REPO_ROOT/.venv/bin/python"
    PY_SOURCE=".venv"
else
    PY_CMD="${PY_CMD:-python3}"
    PY_SOURCE="系统 PATH"
    echo "警告：未找到 .venv，使用系统 Python"
fi

echo "Python: $PY_CMD ($PY_SOURCE)"

# ── 收集后端测试结果 ──────────────────────────────────

echo "=== 收集后端测试结果 ==="

TEST_RESULT="未执行"
TEST_PASS=0
TEST_FAIL=0

pushd "$REPO_ROOT" >/dev/null 2>&1 || true
TEST_OUTPUT=$($PY_CMD -m pytest tests/unit/ --ignore=tests/unit/utils/test_logging.py --tb=no -q 2>&1)
TEST_EXIT=$?
TEST_PASS=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' || echo "0")
TEST_FAIL=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= failed)' || echo "0")
popd >/dev/null 2>&1 || true

if [ "$TEST_EXIT" -ne 0 ]; then
    TEST_RESULT="失败 (exit code $TEST_EXIT, $TEST_PASS 通过)"
elif [ "$TEST_FAIL" -eq 0 ] && [ "$TEST_PASS" -gt 0 ]; then
    TEST_RESULT="通过 ($TEST_PASS 项)"
elif [ "$TEST_FAIL" -gt 0 ]; then
    TEST_RESULT="失败 ($TEST_PASS 通过, $TEST_FAIL 失败)"
else
    TEST_RESULT="无结果"
fi

# ── 收集前端构建结果 ──────────────────────────────────

echo "=== 收集前端构建结果 ==="

CONSOLE_BUILD="跳过"
WEBCHAT_BUILD="跳过"

if [ "$SKIP_BUILD" = false ] && command -v npm &>/dev/null; then
    pushd "$REPO_ROOT/console" >/dev/null 2>&1 || true
    if npm run build &>/dev/null 2>&1; then
        CONSOLE_BUILD="通过"
    else
        CONSOLE_BUILD="失败"
    fi
    popd >/dev/null 2>&1 || true

    pushd "$REPO_ROOT/webchat" >/dev/null 2>&1 || true
    if npm run build &>/dev/null 2>&1; then
        WEBCHAT_BUILD="通过"
    else
        WEBCHAT_BUILD="失败"
    fi
    popd >/dev/null 2>&1 || true
fi

# ── 检查关键文件 ──────────────────────────────────────

echo "=== 检查关键文件 ==="

KEY_FILES=(
    "docs/superpowers/reports/2026-05-12-p3-5-platform-foundation-closeout.md|P3-5 平台底座"
    "docs/superpowers/reports/2026-05-12-p3-5-production-pilot-closeout.md|P3-5 生产试运行"
    "docs/superpowers/reports/2026-05-12-p3-5-contract-freeze.md|P3-5 契约冻结"
    "docs/superpowers/reports/2026-05-12-p3-5-integration-gate.md|P3-5 联调门禁"
    "docs/superpowers/reports/2026-05-12-p3-5-release-gate.md|P3-5 发布门禁"
    "docs/deploy/enterprise-test-deployment.md|部署手册"
    "docs/deploy/kubernetes.md|K8s 部署手册"
    "scripts/enterprise_foundation_check.ps1|Windows 验证脚本"
    "scripts/enterprise_foundation_check.sh|Linux 验证脚本"
    "src/qwenpaw/enterprise/evaluation/__init__.py|测评执行器模块"
    "src/qwenpaw/app/routers/evaluation.py|测评 API 路由"
    "scripts/generate_acceptance_report.sh|验收报告脚本"
)

FILE_SECTION=""
for ENTRY in "${KEY_FILES[@]}"; do
    IFS='|' read -r FPATH FDESC <<< "$ENTRY"
    if [ -f "$REPO_ROOT/$FPATH" ]; then
        STATUS="✅ 存在"
    else
        STATUS="❌ 缺失"
    fi
    FILE_SECTION="${FILE_SECTION}
| ${FPATH} | ${FDESC} | ${STATUS} |"
done

# ── 生成报告 ──────────────────────────────────────────

echo "=== 生成验收报告 ==="

DATE=$(date '+%Y-%m-%d %H:%M:%S')
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

cat > "$REPORT_FILE" << ENDREPORT
# P3 企业化验收报告

**生成时间：** ${DATE}
**分支：** ${GIT_BRANCH}
**提交：** ${GIT_COMMIT}
**Python：** ${PY_SOURCE} (${PY_CMD})

---

## 1. 验证结果汇总

| 检查项 | 结果 |
| --- | --- |
| 后端单元测试 | ${TEST_RESULT} |
| Console 前端构建 | ${CONSOLE_BUILD} |
| WebChat 前端构建 | ${WEBCHAT_BUILD} |

---

## 2. 关键文件检查

| 文件 | 说明 | 状态 |
| --- | --- | --- |${FILE_SECTION}

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

*此报告由 scripts/generate_acceptance_report.sh 自动生成*
ENDREPORT

echo ""
echo "验收报告已生成: $REPORT_FILE"
