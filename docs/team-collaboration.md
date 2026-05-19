# 项目协作手册

**适用范围：** `feature_enterprise` 分支中的企业化能力迭代、产品功能需求澄清、团队协作开发评审和 AI 协作。
**核心原则：** OpenSpec 管需求契约，Superpowers 管执行沉淀，代码评审管实现质量，`AGENTS.md` 管 Agent 快速定位。
**维护方式：** 本文作为团队协作开发规约，随产品需求、团队分工和工程实践持续迭代。

**相关工具 / 技能：**

- [Superpowers 中文技能集](https://github.com/jnMetaCode/superpowers-zh)
- [OpenSpec](https://github.com/Fission-AI/OpenSpec)

## 1. 协作分层

| 层级 | 入口 | 负责人 | 用途 |
| --- | --- | --- | --- |
| 需求契约 | `openspec/` | 需求提出方 + 平台负责人 | 定义能力边界、`SHALL` 要求、验收场景和变更准入 |
| 执行计划 | `docs/superpowers/plans/` | 执行负责人 | 把已确认需求拆成可实施、可验证的任务 |
| 阶段沉淀 | `docs/superpowers/reports/` | 执行负责人 | 记录验证结果、风险、closeout 和 handoff |
| 开发导航 | `AGENTS.md` | 项目维护者 | 给 AI Agent 和新线程快速定位模块、阶段状态和项目禁区 |
| 代码评审 | PR / MR | 模块 Owner | 确认实现质量、测试覆盖、兼容性和发布风险 |

## 2. 产品功能需求进入流程

产品经理提出产品功能需求后，团队按以下顺序推进，避免需求未经方案对齐就直接进入实现：

```text
产品功能需求
  -> 需求分拣：openspec-explore
  -> 方案设计：brainstorming
  -> 契约固化：openspec-propose
  -> 协作计划：writing-plans
  -> 团队实施：subagent-driven-development / executing-plans
  -> 验证评审：requesting-code-review + verification-before-completion
  -> 任务回写：更新 OpenSpec tasks.md
  -> 收口归档：OpenSpec archive / Superpowers reports
```

- **`openspec-explore` 判断「要不要做、边界是什么」：** 澄清 PM 需求目标、影响能力域、现有能力、风险和是否需要 OpenSpec change。
- **`brainstorming` 解决「怎么设计」：** 当产品流程、交互、架构、数据流、跨团队边界或验收方式仍有多种方案时使用，作为进入 OpenSpec 前的方案对齐门。
- **`openspec-propose` 固化「对外契约」：** 新增功能或修改身份、权限、租户、会话、审计、持久化、跨能力域行为时，必须写成可验证的需求契约。
- **`writing-plans` 拆解「怎么实现」：** 契约和方案确认后，再拆成相关团队、模块 Owner、任务顺序、依赖关系、验证命令和不做事项。

本项目中，`brainstorming` 产出的方案结论优先进入 OpenSpec change 的 `design.md`；除非团队明确要求保留独立设计备忘，否则不新增 `docs/superpowers/specs/` 文档。

### 2.1 必须创建 OpenSpec change

以下变更先创建 OpenSpec change，再进入实现：

- 新增用户可见功能或管理能力。
- 修改身份、权限、租户、会话、审计、持久化或跨能力域契约。
- 改变 WebChat、企微 Bot、Enterprise Admin、Skills/MCP、MCP/Tooling、Bad Case 或验收能力的外部行为。

### 2.2 可以直接修复

以下变更可以直接修复，但完成后必须补验证结果：

- 不改变外部契约的 bug 修复。
- 文案、空状态、未开放标识、页面误导性展示修正。
- 测试补充、脚本修正、文档入口补充。

### 2.3 OpenSpec 任务状态规则

- OpenSpec change 的 `tasks.md` 是需求契约进度来源，Superpowers plan 的任务状态不能替代 OpenSpec 任务状态。
- 实现和验证完成后，必须对照本次改动、验证输出和 OpenSpec change 的 `tasks.md`，只勾选已有证据支撑的任务。
- 如果只完成部分任务，未完成项继续保留 `[ ]`，并在实施计划、PR / MR 或阶段报告中说明阻塞、残余风险和下一步。
- 只有 OpenSpec tasks 全部完成、`openspec validate --all --strict` 通过，并经 Owner 确认可以收口后，才归档 OpenSpec change。

## 3. 技能使用速查

团队成员给 AI Agent 分派任务时，应在任务说明中显式写出需要使用的 skill。Agent 命中 skill 后必须读取对应 `SKILL.md`，按当前技能定义执行；如果技能要求和用户当次指令冲突，以用户当次明确指令为准。

| 阶段 | 何时使用 | 建议 skill | 主要产出 |
| --- | --- | --- | --- |
| 产品需求分拣 | PM 提出功能需求后，需要判断目标、边界、影响范围 | `openspec-explore` | 需求边界、影响范围、风险、是否进入 OpenSpec |
| 方案设计 | 需求值得做，但产品流程、架构、数据流或协作接口未定 | `brainstorming` | 方案取舍、关键决策、用户流程、验收口径 |
| 契约创建 | 新增功能或修改共享契约 | `openspec-propose` | proposal、design、spec delta、tasks |
| 计划编写 | 契约或需求已确认，需要拆实施计划 | `writing-plans` | 实施计划、ownership、验证命令 |
| 计划执行 | 从已确认的 Superpowers plan 开始实现 | `executing-plans` / `subagent-driven-development` | 代码、测试、计划任务状态 |
| 任务回写 | 实现和验证完成后，同步 OpenSpec change 状态 | `verification-before-completion` / `openspec-archive-change` | `tasks.md` 勾选、OpenSpec validate 结果、archive 或未完成项说明 |
| Bug 修复 | 测试失败、构建失败、异常行为或修复未生效 | `systematic-debugging` + `test-driven-development` | 根因、回归测试、最小修复 |
| 前端体验 | 修改 Console、WebChat、Enterprise Admin 页面或交互 | `ui-ux-pro-max` + `browser-use` | 设计判断、页面验证、必要截图 |
| 代码审查 | 重要功能完成、合并前、复杂修复后 | `requesting-code-review` + `chinese-code-review` | 按严重级别排列的问题清单 |
| 完成前验证 | 宣称完成、提交、推送或创建 PR 前 | `verification-before-completion` | 新鲜验证命令、退出码、结果和风险 |
| Git 收口 | 提交、分支整理、中文提交说明 | `chinese-commit-conventions` + `chinese-git-workflow` | 符合团队约定的 commit、分支和 PR 信息 |

## 4. 可复制 Agent 模板

默认在同一个会话中围绕同一需求连续推进。只有换线程、换 Agent 或隔天恢复上下文时，才需要补充 `AGENTS.md`、本文、`openspec/README.md`、`docs/superpowers/README.md` 和相关 baseline spec。

### 4.1 产品需求分拣：`openspec-explore`

```text
请使用 `openspec-explore` 对以下 PM 产品功能需求做需求分拣。

需求：
<粘贴 PM 原始需求>

请输出：
- 需求目标和用户价值
- 影响的能力域、前端入口和后端模块
- 现有能力是否已覆盖
- 是否需要 OpenSpec change
- 是否需要进入 `brainstorming` 做方案对齐
- 主要风险、外部依赖和待 PM / Owner 确认的问题

边界：
- 不写代码。
- 不创建实现计划。
- 不修改 OpenSpec 或 Superpowers 文档，除非我明确要求。
```

### 4.2 方案设计：`brainstorming`

```text
请继续使用 `brainstorming`，基于上一步需求分拣结论做方案设计。

请重点对齐：
- 产品流程和用户路径
- 入口、身份、权限、租户、会话、审计的边界
- 前后端数据流和关键状态
- 相关团队、模块 Owner 和协作接口
- 2 到 3 个方案的取舍和推荐方案
- 验收口径和不做事项

产出要求：
- 先给方案和关键决策，等待确认。
- 本项目中不要默认新增 `docs/superpowers/specs/` 文档。
- 如果方案需要固化，建议进入 `openspec-propose`，并把方案结论放入 OpenSpec change 的 `design.md`。
```

### 4.3 契约创建：`openspec-propose`

```text
请继续使用 `openspec-propose`，将已确认方案创建为 OpenSpec change。

请产出：
- proposal.md：说明为什么做、范围和不做事项
- design.md：沉淀方案决策、数据流、协作边界和风险
- specs delta：用 SHALL 写清可验证需求和场景
- tasks.md：只写契约级任务，不替代后续实施计划

完成后运行 `openspec validate --all --strict`。
```

### 4.4 协作计划：`writing-plans`

```text
请继续使用 `writing-plans`，基于已确认的 OpenSpec change 拆协作实施计划。

请输出：
- 相关团队、模块 Owner 和文件 ownership
- 任务顺序、可并行任务和阻塞依赖
- 每个任务涉及的文件或模块范围
- 每个任务的验证命令
- 联调门禁、评审要求和不做事项

计划写入 `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`。
```

### 4.5 团队实施：`subagent-driven-development` 或 `executing-plans`

```text
请继续根据刚生成的实施计划执行实现。

执行方式：
- 如果任务相互独立且文件 ownership 不冲突，使用 `subagent-driven-development`。
- 如果任务耦合较强或需要串行推进，使用 `executing-plans`。

要求：
- 按计划逐项更新状态。
- 不修改计划中不属于当前任务 ownership 的文件，除非先说明原因。
- 修改后运行计划中列出的验证命令。
- 完成实现和验证后，对照 OpenSpec change 的 `tasks.md`，只勾选已有证据支撑的任务；不要只更新 Superpowers plan。
- 完成前使用 `verification-before-completion` 汇总验证结果和残余风险。
```

### 4.6 OpenSpec 任务回写与收口：`verification-before-completion` / `openspec-archive-change`

```text
请继续完成 OpenSpec 任务回写和收口检查。

请执行：
- 对照本次实现、验证输出和 OpenSpec change 的 `tasks.md`。
- 只将已有实现和验证证据支撑的任务改为 `[x]`。
- 未完成任务保留 `[ ]`，并说明阻塞、残余风险和下一步。
- 运行 `openspec validate --all --strict`。
- 如果所有 tasks 已完成且 Owner 确认可以收口，使用 `openspec-archive-change` 归档 change。
- 如需长期留痕，再将验证结果、风险和 closeout 摘要写入 `docs/superpowers/reports/`。
```

## 5. 分支、提交和评审

- 分支名称建议体现能力和模块，例如 `feature/webchat-session-sync`、`fix/enterprise-admin-readiness-state`。
- Commit 使用中文 Conventional Commit：`<type>(scope): <summary>`，summary 使用中文、动词开头、不加句号。
- 一个提交只解决一个清晰问题，避免把需求契约、实现、格式化和无关清理混在一起。
- PR / MR 必须包含需求来源、改动范围、验证结果和风险说明。

## 6. Owner 确认事项

以下事项需要团队 Owner 明确确认，不能只由 Agent 自行判断：

- 真实生产环境凭证、域名、回调地址、可信 IP 和外部 MCP 服务地址。
- 业务口径、业务 SQL、验收问题集和准确率结论。
- 正式验收开始、沟通口径和跨能力域承诺。
- 大规模删除、历史重写、远程推送和敏感配置变更。
