import type { WebchatTask } from "../../../../api/types/tasks";

export interface TaskFormValues {
  name: string;
  enabled: boolean;
  cron: string;
  timezone: string;
  task_type: "agent" | "text";
  content: string;
  timeout_seconds: string;
}

export const DEFAULT_TASK_FORM: TaskFormValues = {
  name: "",
  enabled: true,
  cron: "0 9 * * *",
  timezone: "Asia/Shanghai",
  task_type: "agent",
  content: "",
  timeout_seconds: "120",
};

const DEFAULT_DISPATCH = {
  type: "channel" as const,
  channel: "webchat",
  target: {
    user_id: "webchat",
    session_id: "webchat-task",
  },
  mode: "stream" as const,
  meta: {},
};

function extractContentFromRequest(input: unknown): string {
  if (!Array.isArray(input)) return "";
  const first = input[0];
  if (!first || typeof first !== "object" || !("content" in first)) return "";
  const content = (first as { content?: unknown }).content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  const textPart = content.find(
    (item) =>
      item &&
      typeof item === "object" &&
      "type" in item &&
      "text" in item &&
      (item as { type?: unknown }).type === "text"
  );
  return typeof (textPart as { text?: unknown } | undefined)?.text === "string"
    ? ((textPart as { text: string }).text)
    : "";
}

function toPositiveInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function taskToForm(task: WebchatTask): TaskFormValues {
  const content =
    task.task_type === "text"
      ? task.text || ""
      : extractContentFromRequest(task.request?.input);

  return {
    name: task.name,
    enabled: task.enabled,
    cron: task.schedule.cron,
    timezone: task.schedule.timezone,
    task_type: task.task_type,
    content,
    timeout_seconds: String(task.runtime.timeout_seconds),
  };
}

export function formToTask(
  values: TaskFormValues,
  existingTask?: WebchatTask | null
): WebchatTask {
  const content = values.content.trim();
  const runtime = {
    max_concurrency: existingTask?.runtime.max_concurrency || 1,
    timeout_seconds: toPositiveInt(values.timeout_seconds, 120),
    misfire_grace_seconds: existingTask?.runtime.misfire_grace_seconds || 60,
  };
  const dispatch = existingTask?.dispatch || DEFAULT_DISPATCH;
  const base = {
    id: existingTask?.id || undefined,
    name: values.name.trim(),
    enabled: values.enabled,
    schedule: {
      type: "cron" as const,
      cron: values.cron.trim(),
      timezone: values.timezone,
    },
    dispatch,
    runtime,
    meta: existingTask?.meta || {},
  };

  if (values.task_type === "text") {
    return {
      ...base,
      task_type: "text",
      text: content,
      request: null,
    };
  }

  const target = dispatch.target;
  return {
    ...base,
    task_type: "agent",
    text: null,
    request: {
      input: [
        {
          role: "user",
          type: "message",
          content: [{ type: "text", text: content }],
        },
      ],
      session_id: target.session_id,
      user_id: target.user_id,
    },
  };
}
