import { getAuthStatus } from "@/api/auth"
import { getOpsOverview } from "@/api/ops"
import {
  getVersion,
  getReady,
  getEnterpriseReadiness,
} from "@/api/runtime"
import type {
  AuthStatus,
  VersionInfo,
  ReadyStatus,
  ReadyComponent,
  EnterpriseReadiness,
  OpsOverviewResponse,
} from "@/api/types"

export interface DashboardData {
  authStatus: AuthStatus
  versionInfo: VersionInfo
  readyStatus: ReadyStatus
  enterpriseReadiness: EnterpriseReadiness
  opsOverview: OpsOverviewResponse | null
}

export interface DashboardLoadingState {
  authStatus: boolean
  versionInfo: boolean
  readyStatus: boolean
  enterpriseReadiness: boolean
}

export interface DashboardErrorState {
  authStatus: Error | null
  versionInfo: Error | null
  readyStatus: Error | null
  enterpriseReadiness: Error | null
}

export type ReadyComponentStatus = "ok" | "degraded" | "down"

export interface ReadyComponentView {
  key: string
  name: string
  status: ReadyComponentStatus
  ready: boolean
  scoreWeight: number
  summary?: string
  latencyMs?: number
}

const COMPONENT_LABELS: Record<string, string> = {
  database: "数据库",
  runtime: "运行时",
  storage: "存储",
  audit: "审计",
  observability: "可观测性",
  quota: "配额",
  runtime_extensions: "运行时扩展",
  disk: "磁盘空间",
  backup_dir: "备份目录",
}

function normalizeComponentStatus(
  component: Pick<ReadyComponent, "ready" | "status">,
): ReadyComponentStatus {
  if (component.status === "ok") {
    return "ok"
  }
  if (component.status === "degraded") {
    return "degraded"
  }
  if (component.status === "down") {
    return "down"
  }
  return component.ready === true ? "ok" : "down"
}

function componentScoreWeight(status: ReadyComponentStatus): number {
  if (status === "ok") {
    return 1
  }
  if (status === "degraded") {
    return 0.5
  }
  return 0
}

function stringifyDetailValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return ""
  }
  if (typeof value === "object") {
    return JSON.stringify(value)
  }
  return String(value)
}

function buildComponentSummary(component: ReadyComponent): string | undefined {
  const parts: string[] = []
  if (component.message) {
    parts.push(component.message)
  }
  if (component.details) {
    for (const [key, value] of Object.entries(component.details)) {
      const text = stringifyDetailValue(value)
      if (text) {
        parts.push(`${key}: ${text}`)
      }
    }
  }
  return parts.length > 0 ? parts.join("；") : undefined
}

function toReadyComponentView(component: ReadyComponent): ReadyComponentView {
  const status = normalizeComponentStatus(component)
  return {
    key: component.name,
    name: COMPONENT_LABELS[component.name] || component.name,
    status,
    ready: status === "ok",
    scoreWeight: componentScoreWeight(status),
    summary: buildComponentSummary(component),
    latencyMs: component.latency_ms ?? component.latencyMs,
  }
}

export function getReadyComponentsList(
  readyStatus: ReadyStatus,
): ReadyComponentView[] {
  if (readyStatus.components && readyStatus.components.length > 0) {
    return readyStatus.components.map(toReadyComponentView)
  }

  if (readyStatus.checks) {
    return Object.entries(readyStatus.checks).map(([name, ready]) =>
      toReadyComponentView({
        name,
        ready: ready === true,
      }),
    )
  }

  return []
}

/**
 * 适配层：将后端返回的 ReadyStatus 转换为前端需要的检查状态
 * 后端可能返回 components 数组或 checks 对象
 */
export function adaptReadyStatus(readyStatus: ReadyStatus): Record<string, boolean> {
  return Object.fromEntries(
    getReadyComponentsList(readyStatus).map((component) => [
      component.key,
      component.ready,
    ]),
  )
}

/**
 * 适配层：将后端返回的 EnterpriseReadiness 转换为前端需要的 features
 * 普通用户只返回 { status }，管理员返回 { status, checks, blockers }
 */
/**
 * 适配层：将后端返回的 EnterpriseReadiness 转换为前端 view model
 */
export function adaptEnterpriseReadiness(enterprise: EnterpriseReadiness): {
  status: 'initializing' | 'ready' | 'degraded' | 'error' | 'blocked'
  features: Record<string, boolean>
} {
  // 从 checks 中提取 features（如果有）
  const features: Record<string, boolean> = {
    authz: false,
    audit: false,
    quota: false,
    observability: false,
    policy: false,
    security: false,
    reliability: false,
    compliance: false,
  }

  // 如果有 checks，尝试从中提取 feature 状态
  if (enterprise.checks) {
    for (const [key, value] of Object.entries(enterprise.checks)) {
      features[key] = value === true || (typeof value === 'object' && value !== null && (value as { ready?: boolean }).ready === true)
    }
  }

  // 保留原有 features（如果存在）
  if (enterprise.features) {
    for (const [key, value] of Object.entries(enterprise.features)) {
      if (key in features && value !== undefined) {
        features[key] = value
      }
    }
  }

  const status = (enterprise.status || 'initializing') as 'initializing' | 'ready' | 'degraded' | 'error' | 'blocked'

  return {
    status,
    features,
  }
}

/**
 * 获取 Dashboard 所有数据
 */
export async function fetchDashboardData(): Promise<DashboardData> {
  const [authStatus, versionInfo, readyStatus, enterpriseReadiness, opsOverview] =
    await Promise.all([
      getAuthStatus(),
      getVersion(),
      getReady(),
      getEnterpriseReadiness(),
      getOpsOverview().catch(() => null),
    ])

  return {
    authStatus,
    versionInfo,
    readyStatus,
    enterpriseReadiness,
    opsOverview,
  }
}

/**
 * 计算系统健康状态分数 (0-100)
 */
export function calculateHealthScore(readyStatus: ReadyStatus): number {
  const components = getReadyComponentsList(readyStatus)
  if (components.length === 0) {
    return 0
  }
  const score = components.reduce(
    (total, component) => total + component.scoreWeight,
    0,
  )
  return Math.round((score / components.length) * 100)
}

/**
 * 计算已启用的企业功能数量
 */
export function countEnabledFeatures(
  enterpriseReadiness: EnterpriseReadiness,
): number {
  const adapted = adaptEnterpriseReadiness(enterpriseReadiness)
  const features = Object.values(adapted.features)
  return features.filter(Boolean).length
}

/**
 * 获取系统健康状态的描述文本
 */
export function getHealthStatusText(score: number): {
  text: string
  status: "healthy" | "warning" | "critical"
} {
  if (score >= 80) {
    return { text: "健康", status: "healthy" }
  }
  if (score >= 50) {
    return { text: "警告", status: "warning" }
  }
  return { text: "异常", status: "critical" }
}

/**
 * 获取企业就绪状态的描述文本
 */
export function getReadinessStatusText(
  status: EnterpriseReadiness["status"],
): { label: string; type: "success" | "warning" | "error" | "processing" } {
  const statusMap: Record<
    EnterpriseReadiness["status"],
    { label: string; type: "success" | "warning" | "error" | "processing" }
  > = {
    initializing: { label: "初始化中", type: "processing" },
    ready: { label: "就绪", type: "success" },
    degraded: { label: "降级运行", type: "warning" },
    error: { label: "异常", type: "error" },
    blocked: { label: "阻塞", type: "error" },
  }
  return statusMap[status] || { label: "未知", type: "warning" }
}

/**
 * 格式化版本号显示
 */
export function formatVersion(versionInfo: VersionInfo): string {
  let result = `v${versionInfo.version}`
  if (versionInfo.commit) {
    result += ` (${versionInfo.commit.slice(0, 7)})`
  }
  return result
}

/**
 * 获取企业功能列表
 */
export function getEnterpriseFeaturesList(
  enterpriseReadiness: EnterpriseReadiness,
): Array<{ name: string; key: string; enabled: boolean }> {
  const adapted = adaptEnterpriseReadiness(enterpriseReadiness)
  const featureLabels: Record<string, string> = {
    authz: "权限控制",
    audit: "审计日志",
    quota: "配额管理",
    observability: "可观测性",
    policy: "策略引擎",
    security: "安全加固",
    reliability: "高可用",
    compliance: "合规检查",
  }

  return Object.entries(adapted.features).map(([key, enabled]) => ({
    name: featureLabels[key] || key,
    key,
    enabled,
  }))
}
