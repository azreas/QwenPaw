import { beforeEach, describe, expect, it, vi } from "vitest"
import { getRoot } from "./http"
import { getRawMetrics, parsePrometheusMetrics } from "./metrics"

vi.mock("./http", () => ({
  getRoot: vi.fn(),
}))

describe("metrics api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("parses help, type, labels and sample values", () => {
    const result = parsePrometheusMetrics(`# HELP http_requests_total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",route="/api/version"} 3
http_requests_total{method="POST",route="/api/auth/login"} 2
# TYPE runtime_active gauge
runtime_active 1
`)

    expect(result.metricCount).toBe(2)
    expect(result.sampleCount).toBe(3)
    expect(result.seriesCount).toBe(3)
    expect(result.typeCount).toBe(2)
    expect(result.metrics[0]).toMatchObject({
      name: "http_requests_total",
      type: "counter",
      help: "HTTP requests",
      sampleCount: 2,
      latestValue: 2,
    })
    expect(result.samples[0].labels).toEqual({
      method: "GET",
      route: "/api/version",
    })
  })

  it("ignores blank lines and comments and keeps unlabeled samples", () => {
    const result = parsePrometheusMetrics(`
# just a comment

# HELP runtime_queue Runtime queue depth
# TYPE runtime_queue gauge
runtime_queue 7

`)

    expect(result.metricCount).toBe(1)
    expect(result.sampleCount).toBe(1)
    expect(result.seriesCount).toBe(1)
    expect(result.metrics[0]).toMatchObject({
      name: "runtime_queue",
      type: "gauge",
      help: "Runtime queue depth",
      sampleCount: 1,
      latestValue: 7,
    })
    expect(result.samples[0].labels).toEqual({})
  })

  it("keeps current backend sample-only output as untyped metrics", () => {
    const result = parsePrometheusMetrics(
      'http_requests_total{method="GET",route="/api/version"} 1.0\nruntime_active 1\n',
    )

    expect(result.metricCount).toBe(2)
    expect(result.sampleCount).toBe(2)
    expect(result.metrics[0]).toMatchObject({
      name: "http_requests_total",
      type: "untyped",
      help: "",
      latestValue: 1,
    })
    expect(result.metrics[1]).toMatchObject({
      name: "runtime_active",
      type: "untyped",
      help: "",
      latestValue: 1,
    })
  })

  it("treats observability unavailable text as empty metrics", () => {
    const result = parsePrometheusMetrics("# observability service not available\n")

    expect(result.metricCount).toBe(0)
    expect(result.sampleCount).toBe(0)
    expect(result.seriesCount).toBe(0)
    expect(result.typeCount).toBe(0)
    expect(result.unavailable).toBe(true)
  })

  it("treats empty text as an available empty metrics set", () => {
    const result = parsePrometheusMetrics("")

    expect(result.metricCount).toBe(0)
    expect(result.sampleCount).toBe(0)
    expect(result.seriesCount).toBe(0)
    expect(result.typeCount).toBe(0)
    expect(result.unavailable).toBe(false)
  })

  it("loads raw metrics from root api path", async () => {
    vi.mocked(getRoot).mockResolvedValue("metric 1\n")

    await expect(getRawMetrics()).resolves.toBe("metric 1\n")
    expect(getRoot).toHaveBeenCalledWith("/api/metrics")
  })
})
