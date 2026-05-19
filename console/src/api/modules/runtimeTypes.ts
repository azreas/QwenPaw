export interface RuntimeHealthResponse {
  status: string;
}

export interface RuntimeComponentStatus {
  name: string;
  status: string;
  detail?: string;
}

export interface RuntimeReadinessResponse {
  ready: boolean;
  status: string;
  components: RuntimeComponentStatus[];
}

export interface RuntimeReadinessSummary {
  ready: boolean;
  status: string;
  failedComponents: string[];
}

export function summarizeReadiness(
  report: RuntimeReadinessResponse,
): RuntimeReadinessSummary {
  return {
    ready: report.ready,
    status: report.status,
    failedComponents: report.components
      .filter((component) => component.status === "down")
      .map((component) => component.name),
  };
}
