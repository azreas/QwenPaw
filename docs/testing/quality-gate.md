# Quality Gate

## Backend

企业运行时定向测试 + 覆盖率门禁：

```bash
pytest tests/unit/enterprise tests/unit/app tests/unit/routers tests/e2e tests/performance \
  --cov=src/qwenpaw/enterprise \
  --cov=src/qwenpaw/tenancy \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing
python scripts/quality/coverage_gate.py --xml coverage.xml --min 80
```

注意：覆盖率度量范围限定为企业模块（`enterprise`）和租户模块（`tenancy`），不度量全仓。

## Frontend

```bash
cd console && npm install && npm exec -- tsc -b --noEmit
cd webchat && npm install && npm exec -- tsc -p tsconfig.json --noEmit
```

## Performance Smoke

```bash
pytest tests/performance/test_api_smoke.py -q
```

## CI

PR 触发 `.github/workflows/quality-gate.yml`，包含：

- 企业模块定向测试 + 覆盖率报告
- 80% 覆盖率门禁
- Console / WebChat TypeScript 类型检查

## 排障

- **coverage gate 失败**：查看 `--cov-report=term-missing` 输出中标记的未覆盖行
- **前端 TS 错误**：先 `npm install` 确保依赖最新，再 `tsc --noEmit`
- **E2E 403**：`/api/metrics` 在无 enterprise_runtime 时返回 403 是预期行为
