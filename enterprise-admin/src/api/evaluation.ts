import { del, get, patch, post } from "./http"
import type {
  AccuracyReport,
  AcceptanceEvidenceExport,
  AddEvalItemsRequest,
  BadCaseToEvalRequest,
  BadCaseToEvalResult,
  CreateEvalDatasetRequest,
  CreateEvalExecutionRequest,
  EvalDataset,
  EvalDatasetListResponse,
  EvalExecution,
  EvalExecutionListResponse,
  EvalExecutionQuery,
  UpdateEvalDatasetRequest,
} from "./types"

const EVALUATION_BASE = "/evaluation"

function tenantEvaluationBase(agentId: string): string {
  return `${EVALUATION_BASE}/tenants/${encodeURIComponent(agentId)}`
}

function assertNonEmptyId(value: string, label: string): string {
  const normalized = value.trim()
  if (!normalized) {
    throw new Error(`${label} is required`)
  }
  return normalized
}

function tenantDatasetCollectionUrl(agentId: string): string {
  return `${tenantEvaluationBase(agentId)}/datasets`
}

function tenantDatasetUrl(agentId: string, datasetId: string): string {
  return `${tenantDatasetCollectionUrl(agentId)}/${encodeURIComponent(datasetId)}`
}

function tenantExecutionCollectionUrl(agentId: string): string {
  return `${tenantEvaluationBase(agentId)}/executions`
}

function tenantExecutionUrl(agentId: string, executionId: string): string {
  return `${tenantExecutionCollectionUrl(agentId)}/${encodeURIComponent(executionId)}`
}

export async function listTenantEvalDatasets(
  agentId: string,
): Promise<EvalDatasetListResponse> {
  return get<EvalDatasetListResponse>(tenantDatasetCollectionUrl(agentId))
}

export async function createTenantEvalDataset(
  agentId: string,
  data: CreateEvalDatasetRequest,
): Promise<EvalDataset> {
  return post<EvalDataset>(tenantDatasetCollectionUrl(agentId), data)
}

export async function getSampleEvalDataset(): Promise<EvalDataset> {
  return get<EvalDataset>(`${EVALUATION_BASE}/datasets/sample`)
}

export async function getTenantEvalDataset(
  agentId: string,
  datasetId: string,
): Promise<EvalDataset> {
  return get<EvalDataset>(
    tenantDatasetUrl(agentId, assertNonEmptyId(datasetId, "datasetId")),
  )
}

export async function updateTenantEvalDataset(
  agentId: string,
  datasetId: string,
  data: UpdateEvalDatasetRequest,
): Promise<EvalDataset> {
  return patch<EvalDataset>(
    tenantDatasetUrl(agentId, assertNonEmptyId(datasetId, "datasetId")),
    data,
  )
}

export async function addTenantEvalItems(
  agentId: string,
  datasetId: string,
  data: AddEvalItemsRequest,
): Promise<EvalDataset> {
  return post<EvalDataset>(
    `${tenantDatasetUrl(agentId, assertNonEmptyId(datasetId, "datasetId"))}/items`,
    data,
  )
}

export async function deleteTenantEvalDataset(
  agentId: string,
  datasetId: string,
): Promise<void> {
  return del<void>(
    tenantDatasetUrl(agentId, assertNonEmptyId(datasetId, "datasetId")),
  )
}

export async function listTenantEvalExecutions(
  agentId: string,
  query?: EvalExecutionQuery,
): Promise<EvalExecutionListResponse> {
  return get<EvalExecutionListResponse>(tenantExecutionCollectionUrl(agentId), {
    params: query,
  })
}

export async function createTenantEvalExecution(
  agentId: string,
  data: CreateEvalExecutionRequest,
): Promise<EvalExecution> {
  return post<EvalExecution>(tenantExecutionCollectionUrl(agentId), data)
}

export async function getTenantEvalExecution(
  agentId: string,
  executionId: string,
): Promise<EvalExecution> {
  return get<EvalExecution>(
    tenantExecutionUrl(agentId, assertNonEmptyId(executionId, "executionId")),
  )
}

export async function getTenantAccuracyReport(
  agentId: string,
  executionId: string,
): Promise<AccuracyReport> {
  return get<AccuracyReport>(
    `${tenantExecutionUrl(agentId, assertNonEmptyId(executionId, "executionId"))}/report`,
  )
}

export async function exportTenantAcceptanceEvidence(
  agentId: string,
  executionId: string,
): Promise<AcceptanceEvidenceExport> {
  return get<AcceptanceEvidenceExport>(
    `${tenantExecutionUrl(agentId, assertNonEmptyId(executionId, "executionId"))}/evidence`,
  )
}

export async function convertBadCasesToEval(
  agentId: string,
  data: BadCaseToEvalRequest,
): Promise<BadCaseToEvalResult> {
  return post<BadCaseToEvalResult>(
    `${tenantEvaluationBase(agentId)}/bad-case-to-eval`,
    data,
  )
}
