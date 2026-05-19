import type {
  WecomTenantCronJob,
  WecomTenantCronJobInput,
} from "../../../../../api/types";

export interface CronFormValues {
  id: string;
  name: string;
  enabled: boolean;
  cron: string;
  timezone: string;
  task_type: "text" | "agent";
  text: string;
  channel: string;
  mode: "stream" | "final";
  user_id: string;
  session_id: string;
  advancedJson: string;
}

export const DEFAULT_JOB: CronFormValues = {
  id: "",
  name: "daily-check",
  enabled: true,
  cron: "0 9 * * *",
  timezone: "UTC",
  task_type: "text",
  text: "请总结当前租户状态",
  channel: "console",
  mode: "stream",
  user_id: "admin",
  session_id: "wecom-tenant-cron",
  advancedJson: "{}",
};

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function compactObject(value: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined),
  );
}

export function readableError(error: unknown): string {
  const message = (error as Error).message || String(error);
  return message.split(" - ")[0] || message;
}

export function formatRuntimeTime(value: unknown): string {
  if (!value) return "-";
  if (typeof value === "number") {
    const date = new Date(value > 10_000_000_000 ? value : value * 1000);
    return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
  }
  if (typeof value === "string") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }
  return "-";
}

export function jobRuntimeValue(job: WecomTenantCronJob, key: string): unknown {
  return (job as unknown as Record<string, unknown>)[key];
}

export function jobToForm(job: WecomTenantCronJob): CronFormValues {
  const advanced = compactObject({
    request: job.request,
    runtime: job.runtime,
    meta: job.meta,
    dispatch_meta: job.dispatch?.meta,
  });
  return {
    id: job.id || "",
    name: job.name || "",
    enabled: job.enabled ?? true,
    cron:
      job.schedule?.type === "cron" ? job.schedule.cron : "0 9 * * *",
    timezone: job.schedule?.timezone || "UTC",
    task_type: job.task_type || "text",
    text: job.text || "",
    channel: job.dispatch?.channel || "console",
    mode: job.dispatch?.mode || "stream",
    user_id: job.dispatch?.target?.user_id || "admin",
    session_id: job.dispatch?.target?.session_id || "wecom-tenant-cron",
    advancedJson: prettyJson(advanced),
  };
}

export function valuesToPayload(values: CronFormValues): WecomTenantCronJobInput {
  const advanced = JSON.parse(values.advancedJson || "{}") as Record<string, unknown>;
  const dispatchMeta = advanced.dispatch_meta as Record<string, unknown> | undefined;
  delete advanced.dispatch_meta;

  const payload = {
    ...advanced,
    id: values.id || "",
    name: values.name,
    enabled: values.enabled,
    schedule: {
      type: "cron",
      cron: values.cron,
      timezone: values.timezone || "UTC",
    },
    task_type: values.task_type,
    dispatch: {
      type: "channel",
      channel: values.channel || "console",
      mode: values.mode || "stream",
      target: {
        user_id: values.user_id,
        session_id: values.session_id,
      },
      meta: dispatchMeta || {},
    },
  } as WecomTenantCronJobInput;

  if (values.task_type === "text") {
    payload.text = values.text;
  } else {
    payload.request = payload.request || { input: values.text || "" };
  }
  return payload;
}
