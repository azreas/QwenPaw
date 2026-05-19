import { getRoot } from "./http"
import type {
  MetricSample,
  MetricSummaryItem,
  MetricsSummary,
  PrometheusMetricType,
} from "./types"

const HELP_PATTERN = /^# HELP\s+(\S+)\s+(.+)$/
const TYPE_PATTERN =
  /^# TYPE\s+(\S+)\s+(counter|gauge|histogram|summary|untyped)$/
const SAMPLE_PATTERN =
  /^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+(-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)$/

export function getRawMetrics(): Promise<string> {
  return getRoot<string>("/api/metrics")
}

export function parsePrometheusMetrics(raw: string): MetricsSummary {
  const helpByName = new Map<string, string>()
  const typeByName = new Map<string, PrometheusMetricType>()
  const samples: MetricSample[] = []
  const unavailable = raw.includes("observability service not available")

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed) {
      continue
    }

    const helpMatch = trimmed.match(HELP_PATTERN)
    if (helpMatch) {
      helpByName.set(helpMatch[1], helpMatch[2])
      continue
    }

    const typeMatch = trimmed.match(TYPE_PATTERN)
    if (typeMatch) {
      typeByName.set(typeMatch[1], typeMatch[2] as PrometheusMetricType)
      continue
    }

    if (trimmed.startsWith("#")) {
      continue
    }

    const sampleMatch = trimmed.match(SAMPLE_PATTERN)
    if (!sampleMatch) {
      continue
    }

    samples.push({
      name: sampleMatch[1],
      labels: parseLabels(sampleMatch[2] ?? ""),
      value: Number(sampleMatch[3]),
      raw: trimmed,
    })
  }

  const sampleMap = new Map<string, MetricSample[]>()
  for (const sample of samples) {
    const metricSamples = sampleMap.get(sample.name) ?? []
    metricSamples.push(sample)
    sampleMap.set(sample.name, metricSamples)
  }

  const metrics: MetricSummaryItem[] = Array.from(sampleMap.entries()).map(
    ([name, metricSamples]) => ({
      name,
      type: typeByName.get(name) ?? "untyped",
      help: helpByName.get(name) ?? "",
      sampleCount: metricSamples.length,
      latestValue: metricSamples[metricSamples.length - 1]?.value,
    }),
  )

  return {
    raw,
    metrics,
    samples,
    metricCount: metrics.length,
    sampleCount: samples.length,
    seriesCount: new Set(samples.map((sample) => sample.raw.split(/\s+/)[0])).size,
    typeCount: new Set(metrics.map((metric) => metric.type)).size,
    unavailable,
  }
}

function parseLabels(rawLabels: string): Record<string, string> {
  if (!rawLabels) {
    return {}
  }

  const labels: Record<string, string> = {}
  for (const pair of rawLabels.split(",")) {
    const match = pair.match(/^\s*([^=]+)="(.*)"\s*$/)
    if (!match) {
      return {}
    }
    labels[match[1]] = match[2]
  }

  return labels
}
