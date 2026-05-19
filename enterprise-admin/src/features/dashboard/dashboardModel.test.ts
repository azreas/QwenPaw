import { describe, it, expect, vi, beforeEach } from "vitest"
import { getOpsOverview } from "@/api/ops"
import {
  calculateHealthScore,
  countEnabledFeatures,
  getHealthStatusText,
  getReadinessStatusText,
  formatVersion,
  getEnterpriseFeaturesList,
  adaptReadyStatus,
  getReadyComponentsList,
  fetchDashboardData,
} from "./dashboardModel"

vi.mock("@/api/ops", () => ({
  getOpsOverview: vi.fn(),
}))

vi.mock("@/api/auth", () => ({
  getAuthStatus: vi.fn().mockResolvedValue({ authenticated: true }),
}))

vi.mock("@/api/runtime", () => ({
  getVersion: vi.fn().mockResolvedValue({ version: "1.0.0" }),
  getReady: vi.fn().mockResolvedValue({
    ready: true,
    checks: {
      database: true,
      runtime: true,
      storage: true,
    },
  }),
  getEnterpriseReadiness: vi.fn().mockResolvedValue({
    enabled: true,
    status: "ready",
    storageBackend: "sqlite",
    features: {
      authz: true,
      audit: true,
      quota: true,
      observability: true,
      policy: true,
      security: true,
      reliability: true,
      compliance: true,
    },
  }),
}))

describe("dashboardModel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getOpsOverview).mockReset()
  })

  describe("fetchDashboardData", () => {
    it("fetches ops overview for dashboard aggregation", async () => {
      vi.mocked(getOpsOverview).mockResolvedValue({
        total_tenants: 2,
        running_tenants: 1,
        unhealthy_tenants: 1,
        business_calls_24h: 42,
        failed_calls_24h: 5,
        failure_rate: 0.119,
        entrypoints: {
          webchat: 30,
          wecom_bot: 12,
        },
        top_failed_abilities: [
          {
            ability_name: "sales-query",
            ability_type: "skill",
            count: 3,
            last_error: "timeout",
          },
        ],
      })

      const data = await fetchDashboardData()

      expect(data.opsOverview?.business_calls_24h).toBe(42)
      expect(data.opsOverview?.failed_calls_24h).toBe(5)
    })

    it("keeps dashboard usable when ops overview is denied or unavailable", async () => {
      vi.mocked(getOpsOverview).mockRejectedValue(new Error("forbidden"))

      const data = await fetchDashboardData()

      expect(data.opsOverview).toBeNull()
      expect(data.readyStatus).toBeDefined()
    })
  })

  describe("adaptReadyStatus", () => {
    it("应该正确适配 components 数组格式并保留动态组件", () => {
      const readyStatus = {
        ready: true,
        components: [
          { name: "storage", status: "ok", message: "" },
          { name: "audit", status: "degraded", message: "not configured" },
          {
            name: "runtime_extensions",
            status: "down",
            message: "extension probe failed",
            details: { gateway: "unreachable" },
          },
        ],
      }
      expect(adaptReadyStatus(readyStatus)).toEqual({
        storage: true,
        audit: false,
        runtime_extensions: false,
      })
    })

    it("应该降级使用 checks 对象格式", () => {
      const readyStatus = {
        ready: true,
        checks: {
          database: true,
          runtime: true,
          storage: false,
        },
      }
      expect(adaptReadyStatus(readyStatus)).toEqual({
        database: true,
        runtime: true,
        storage: false,
      })
    })

    it("无数据时应返回空状态", () => {
      const readyStatus = { ready: false }
      expect(adaptReadyStatus(readyStatus)).toEqual({})
    })
  })

  describe("getReadyComponentsList", () => {
    it("应该按后端真实组件名展示状态和原因摘要", () => {
      const readyStatus = {
        ready: false,
        components: [
          { name: "storage", status: "ok", details: { backend: "sqlite" } },
          { name: "audit", status: "degraded", message: "not configured" },
          {
            name: "runtime_extensions",
            status: "down",
            message: "extension probe failed",
            details: { gateway: "unreachable" },
            latency_ms: 12.4,
          },
        ],
      }

      expect(getReadyComponentsList(readyStatus)).toEqual([
        {
          key: "storage",
          name: "存储",
          status: "ok",
          ready: true,
          scoreWeight: 1,
          summary: "backend: sqlite",
          latencyMs: undefined,
        },
        {
          key: "audit",
          name: "审计",
          status: "degraded",
          ready: false,
          scoreWeight: 0.5,
          summary: "not configured",
          latencyMs: undefined,
        },
        {
          key: "runtime_extensions",
          name: "运行时扩展",
          status: "down",
          ready: false,
          scoreWeight: 0,
          summary: "extension probe failed；gateway: unreachable",
          latencyMs: 12.4,
        },
      ])
    })

    it("应该保留旧 checks 兼容", () => {
      const readyStatus = {
        ready: true,
        checks: {
          database: true,
          runtime: true,
          storage: false,
        },
      }

      expect(getReadyComponentsList(readyStatus).map((item) => item.key)).toEqual([
        "database",
        "runtime",
        "storage",
      ])
    })
  })

  describe("calculateHealthScore", () => {
    it("所有检查通过时应该返回100分", () => {
      const readyStatus = {
        ready: true,
        checks: {
          database: true,
          runtime: true,
          storage: true,
        },
      }
      expect(calculateHealthScore(readyStatus)).toBe(100)
    })

    it("components 格式下应基于真实状态计算分数", () => {
      const readyStatus = {
        ready: false,
        components: [
          { name: "storage", status: "ok" },
          { name: "audit", status: "degraded", message: "not configured" },
          { name: "runtime_extensions", status: "down" },
        ],
      }
      expect(calculateHealthScore(readyStatus)).toBe(50)
    })

    it("部分检查通过时应该返回相应的分数", () => {
      const readyStatus = {
        ready: true,
        checks: {
          database: true,
          runtime: false,
          storage: true,
        },
      }
      expect(calculateHealthScore(readyStatus)).toBe(67)
    })

    it("所有检查失败时应该返回0分", () => {
      const readyStatus = {
        ready: false,
        checks: {
          database: false,
          runtime: false,
          storage: false,
        },
      }
      expect(calculateHealthScore(readyStatus)).toBe(0)
    })

    it("无 components 和 checks 时应该返回0分且不除零", () => {
      expect(calculateHealthScore({ ready: false })).toBe(0)
    })
  })

  describe("countEnabledFeatures", () => {
    it("应该正确计算已启用的功能数量", () => {
      const enterpriseReadiness = {
        enabled: true,
        features: {
          authz: true,
          audit: true,
          quota: false,
          observability: true,
          policy: false,
          security: true,
          reliability: true,
          compliance: false,
        },
        storageBackend: "sqlite",
        status: "ready" as const,
      }
      expect(countEnabledFeatures(enterpriseReadiness)).toBe(5)
    })

    it("所有功能都启用时应该返回总数量", () => {
      const enterpriseReadiness = {
        enabled: true,
        features: {
          authz: true,
          audit: true,
          quota: true,
          observability: true,
          policy: true,
          security: true,
          reliability: true,
          compliance: true,
        },
        storageBackend: "sqlite",
        status: "ready" as const,
      }
      expect(countEnabledFeatures(enterpriseReadiness)).toBe(8)
    })

    it("没有功能启用时应该返回0", () => {
      const enterpriseReadiness = {
        enabled: false,
        features: {
          authz: false,
          audit: false,
          quota: false,
          observability: false,
          policy: false,
          security: false,
          reliability: false,
          compliance: false,
        },
        storageBackend: "sqlite",
        status: "initializing" as const,
      }
      expect(countEnabledFeatures(enterpriseReadiness)).toBe(0)
    })
  })

  describe("getHealthStatusText", () => {
    it("高分应该返回健康状态", () => {
      expect(getHealthStatusText(100)).toEqual({
        text: "健康",
        status: "healthy",
      })
      expect(getHealthStatusText(80)).toEqual({
        text: "健康",
        status: "healthy",
      })
    })

    it("中等分数应该返回警告状态", () => {
      expect(getHealthStatusText(67)).toEqual({
        text: "警告",
        status: "warning",
      })
      expect(getHealthStatusText(50)).toEqual({
        text: "警告",
        status: "warning",
      })
    })

    it("低分应该返回异常状态", () => {
      expect(getHealthStatusText(33)).toEqual({
        text: "异常",
        status: "critical",
      })
      expect(getHealthStatusText(0)).toEqual({
        text: "异常",
        status: "critical",
      })
    })
  })

  describe("getReadinessStatusText", () => {
    it("应该正确映射initializing状态", () => {
      expect(getReadinessStatusText("initializing")).toEqual({
        label: "初始化中",
        type: "processing",
      })
    })

    it("应该正确映射ready状态", () => {
      expect(getReadinessStatusText("ready")).toEqual({
        label: "就绪",
        type: "success",
      })
    })

    it("应该正确映射degraded状态", () => {
      expect(getReadinessStatusText("degraded")).toEqual({
        label: "降级运行",
        type: "warning",
      })
    })

    it("应该正确映射error状态", () => {
      expect(getReadinessStatusText("error")).toEqual({
        label: "异常",
        type: "error",
      })
    })

    it("应该正确映射blocked状态", () => {
      expect(getReadinessStatusText("blocked")).toEqual({
        label: "阻塞",
        type: "error",
      })
    })
  })

  describe("formatVersion", () => {
    it("应该正确格式化只有version的情况", () => {
      const versionInfo = {
        version: "1.0.0",
      }
      expect(formatVersion(versionInfo)).toBe("v1.0.0")
    })

    it("应该正确格式化带commit的版本", () => {
      const versionInfo = {
        version: "1.0.0",
        commit: "abcdef1234567890",
      }
      expect(formatVersion(versionInfo)).toBe("v1.0.0 (abcdef1)")
    })

    it("应该正确格式化带buildTime的版本", () => {
      const versionInfo = {
        version: "1.0.0",
        buildTime: "2024-01-01T00:00:00Z",
      }
      expect(formatVersion(versionInfo)).toBe("v1.0.0")
    })
  })

  describe("getEnterpriseFeaturesList", () => {
    it("应该正确返回功能列表", () => {
      const enterpriseReadiness = {
        enabled: true,
        status: "ready" as const,
        features: {
          authz: true,
          audit: false,
          quota: true,
          observability: false,
          policy: true,
          security: false,
          reliability: true,
          compliance: false,
        },
      }

      const result = getEnterpriseFeaturesList(enterpriseReadiness)

      expect(result).toHaveLength(8)
      expect(result.find((f) => f.key === "authz")).toEqual({
        name: "权限控制",
        key: "authz",
        enabled: true,
      })
      expect(result.find((f) => f.key === "audit")).toEqual({
        name: "审计日志",
        key: "audit",
        enabled: false,
      })
      expect(result.find((f) => f.key === "quota")).toEqual({
        name: "配额管理",
        key: "quota",
        enabled: true,
      })
    })

    it("对于未知的feature key应该使用key作为名称", () => {
      const enterpriseReadiness = {
        enabled: true,
        status: "ready" as const,
        checks: {
          unknownFeature: true,
        },
      } as any

      const result = getEnterpriseFeaturesList(enterpriseReadiness)

      const unknownFeature = result.find((f) => f.key === "unknownFeature")
      expect(unknownFeature).toBeDefined()
      expect(unknownFeature?.name).toBe("unknownFeature")
      expect(unknownFeature?.enabled).toBe(true)
    })
  })
})
