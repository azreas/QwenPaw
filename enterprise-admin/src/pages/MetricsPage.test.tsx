import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { getRawMetrics, parsePrometheusMetrics } from "@/api/metrics"
import type { MetricsSummary } from "@/api/types"
import MetricsPage from "./MetricsPage"

vi.mock("@/api/metrics", () => ({
  getRawMetrics: vi.fn(),
  parsePrometheusMetrics: vi.fn(),
}))

function buildSummary(overrides: Partial<MetricsSummary> = {}): MetricsSummary {
  return {
    raw: `# HELP http_requests_total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",route="/api/version"} 3
runtime_active 1
`,
    metrics: [
      {
        name: "http_requests_total",
        type: "counter",
        help: "HTTP requests",
        sampleCount: 1,
        latestValue: 3,
      },
      {
        name: "runtime_active",
        type: "gauge",
        help: "Runtime active",
        sampleCount: 1,
        latestValue: 1,
      },
    ],
    samples: [
      {
        name: "http_requests_total",
        labels: {
          method: "GET",
          route: "/api/version",
        },
        value: 3,
        raw: `http_requests_total{method="GET",route="/api/version"} 3`,
      },
      {
        name: "runtime_active",
        labels: {},
        value: 1,
        raw: "runtime_active 1",
      },
    ],
    metricCount: 2,
    sampleCount: 2,
    seriesCount: 2,
    typeCount: 2,
    unavailable: false,
    ...overrides,
  }
}

describe("MetricsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders summary cards, staged notice, completeness panel and raw preview", async () => {
    const raw = `http_requests_total{method="GET",route="/api/version"} 3
runtime_active 1
`
    const summary = buildSummary({
      raw,
      metrics: [
        {
          name: "http_requests_total",
          type: "untyped",
          help: "",
          sampleCount: 1,
          latestValue: 3,
        },
        {
          name: "runtime_active",
          type: "untyped",
          help: "",
          sampleCount: 1,
          latestValue: 1,
        },
      ],
    })
    vi.mocked(getRawMetrics).mockResolvedValue(raw)
    vi.mocked(parsePrometheusMetrics).mockReturnValue(summary)

    render(<MetricsPage />)

    expect(
      await screen.findByRole("heading", { name: "指标监控" }),
    ).toBeInTheDocument()
    expect(
      screen.getByText("Prometheus 指标只读摘要和原始预览"),
    ).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
    expect(screen.getByText("指标名称数")).toBeInTheDocument()
    expect(screen.getAllByText("样本数").length).toBeGreaterThan(0)
    expect(screen.getByText("活跃序列数")).toBeInTheDocument()
    expect(screen.getByText("指标类型数")).toBeInTheDocument()
    expect(screen.getByText("告警/趋势/导出/跨租户下钻阶段化开放")).toBeInTheDocument()
    expect(screen.getByText("http_requests_total")).toBeInTheDocument()
    expect(
      screen.getByText(/http_requests_total\{method="GET",route="\/api\/version"\} 3/),
    ).toBeInTheDocument()
    expect(getRawMetrics).toHaveBeenCalledTimes(1)
    expect(parsePrometheusMetrics).toHaveBeenCalledWith(raw)
  })

  it("renders observability unavailable empty state", async () => {
    const raw = "# observability service not available\n"
    vi.mocked(getRawMetrics).mockResolvedValue(raw)
    vi.mocked(parsePrometheusMetrics).mockReturnValue(
      buildSummary({
        raw,
        metrics: [],
        samples: [],
        metricCount: 0,
        sampleCount: 0,
        seriesCount: 0,
        typeCount: 0,
        unavailable: true,
      }),
    )

    render(<MetricsPage />)

    expect(await screen.findByText("Observability 未启用")).toBeInTheDocument()
    expect(
      screen.getByText("当前环境未启用指标观测服务，/api/metrics 返回了只读占位说明。"),
    ).toBeInTheDocument()
  })

  it("renders empty metrics state when raw metrics has no samples", async () => {
    const raw = "# HELP placeholder no data\n"
    vi.mocked(getRawMetrics).mockResolvedValue(raw)
    vi.mocked(parsePrometheusMetrics).mockReturnValue(
      buildSummary({
        raw,
        metrics: [],
        samples: [],
        metricCount: 0,
        sampleCount: 0,
        seriesCount: 0,
        typeCount: 0,
      }),
    )

    render(<MetricsPage />)

    expect(await screen.findByText("暂无可用指标")).toBeInTheDocument()
    expect(
      screen.getByText("当前未解析到 Prometheus 样本，可先检查 observability registry 或指标采集状态。"),
    ).toBeInTheDocument()
  })

  it("renders persistent error state when metrics request fails", async () => {
    vi.mocked(getRawMetrics).mockRejectedValue(new Error("metrics unavailable"))

    render(<MetricsPage />)

    expect(await screen.findByText("加载指标监控失败")).toBeInTheDocument()
    expect(screen.getByText("metrics unavailable")).toBeInTheDocument()
    expect(parsePrometheusMetrics).not.toHaveBeenCalled()
  })
})
