import { describe, expect, it } from "vitest"
import {
  buildAbilityStats,
  formatDurationMs,
  getAbilityStatusTag,
  getConnectionTestTag,
  getLastCallText,
} from "./abilityModel"
import type { MCPClientInfo, SkillInfo, ToolInfo } from "@/api/types"

const skills: SkillInfo[] = [
  {
    name: "sales_report",
    description: "销售报表",
    source: "workspace",
    enabled: true,
    installed: true,
    installable: false,
    channels: ["wecom_tenant"],
    tags: ["sales"],
    requirements: [],
    last_call_status: "success",
    last_duration_ms: 45,
  },
  {
    name: "finance_query",
    description: "财务查询",
    source: "uploaded_media",
    enabled: false,
    installed: false,
    installable: true,
    channels: [],
    tags: [],
    requirements: [],
    last_call_status: "failure",
    last_error_reason: "missing env",
  },
]

const mcps: MCPClientInfo[] = [
  {
    client_key: "erp",
    name: "ERP",
    description: "ERP MCP",
    enabled: true,
    transport: "streamable_http",
    url: "https://mcp.example.com",
    command: "",
    args: [],
    cwd: "",
    headers: {},
    env: {},
    last_call_status: "failure",
    last_test_status: "ok",
    last_duration_ms: 1200,
  },
]

const tools: ToolInfo[] = [
  {
    name: "read_file",
    description: "Read files",
    enabled: true,
    async_execution: false,
    icon: "",
  },
  {
    name: "write_file",
    description: "Write files",
    enabled: false,
    async_execution: true,
    icon: "",
  },
]

describe("abilityModel", () => {
  it("构建能力统计", () => {
    expect(buildAbilityStats(skills, mcps, tools)).toEqual({
      totalSkills: 2,
      enabledSkills: 1,
      installableSkills: 1,
      totalMcpClients: 1,
      enabledMcpClients: 1,
      totalTools: 2,
      enabledTools: 1,
      failedCalls: 2,
    })
  })

  it("映射状态标签", () => {
    expect(getAbilityStatusTag(true)).toEqual({ text: "已启用", color: "green" })
    expect(getAbilityStatusTag(false)).toEqual({ text: "已停用", color: "default" })
    expect(getConnectionTestTag("ok")).toEqual({ text: "连接正常", color: "green" })
    expect(getConnectionTestTag("timeout")).toEqual({ text: "连接超时", color: "orange" })
    expect(getConnectionTestTag("auth_failed")).toEqual({ text: "认证失败", color: "red" })
    expect(getConnectionTestTag()).toEqual({ text: "未测试", color: "default" })
  })

  it("格式化耗时", () => {
    expect(formatDurationMs(45)).toBe("45ms")
    expect(formatDurationMs(999.4)).toBe("999ms")
    expect(formatDurationMs(1200)).toBe("1.20s")
    expect(formatDurationMs()).toBe("-")
  })

  it("生成最近调用摘要时优先展示错误原因，其次耗时", () => {
    expect(getLastCallText(skills[0])).toBe("success / 45ms")
    expect(getLastCallText(skills[1])).toBe("failure / missing env")
    expect(
      getLastCallText({
        last_call_status: "failure",
        last_error_reason: "auth failed",
        last_duration_ms: 1200,
      }),
    ).toBe("failure / auth failed")
    expect(getLastCallText({ last_call_status: "success" })).toBe("success / -")
    expect(getLastCallText({})).toBe("-")
  })
})
