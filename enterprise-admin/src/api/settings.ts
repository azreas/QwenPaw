import { get } from "./http"
import type {
  ComplianceExportRequest,
  PlatformSettingsSummary,
} from "./types"
import axios from "axios"

export function getPlatformSettingsSummary(): Promise<PlatformSettingsSummary> {
  return get<PlatformSettingsSummary>("/settings/platform-summary")
}

export async function exportComplianceAudit(
  payload: ComplianceExportRequest,
): Promise<{ blob: Blob; filename: string }> {
  const response = await axios.request<Blob>({
    method: "POST",
    url: `/api/compliance/audit/export`,
    data: payload,
    responseType: "blob",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("enterprise_admin_token") || ""}`,
    },
  })

  const contentDisposition = response.headers["content-disposition"]
  const filename = extractDownloadFilename(contentDisposition, payload.format)
  return { blob: response.data, filename }
}

export function extractDownloadFilename(
  contentDisposition: string | null | undefined,
  format: ComplianceExportRequest["format"],
): string {
  const fallback = `audit-export.${format}`
  if (!contentDisposition) {
    return fallback
  }
  const match = contentDisposition.match(/filename="?([^";]+)"?/i)
  return match?.[1] || fallback
}
