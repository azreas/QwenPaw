import { request } from "../request";
import { rootRequest } from "../rootRequest.ts";
import type {
  RuntimeHealthResponse,
  RuntimeReadinessResponse,
} from "./runtimeTypes";
export type {
  RuntimeHealthResponse,
  RuntimeComponentStatus,
  RuntimeReadinessResponse,
  RuntimeReadinessSummary,
} from "./runtimeTypes";
export { summarizeReadiness } from "./runtimeTypes";

export const runtimeApi = {
  getHealth: () => rootRequest<RuntimeHealthResponse>("/health"),
  getReady: () =>
    rootRequest<RuntimeReadinessResponse>("/ready", { allowedStatuses: [503] }),
  getMetrics: () =>
    request<string>("/metrics", {
      headers: { Accept: "text/plain; version=0.0.4" },
    }),
};
