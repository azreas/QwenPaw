export interface TaskSchedule {
  type: "cron";
  cron: string;
  timezone: string;
}

export interface TaskRuntime {
  max_concurrency: number;
  timeout_seconds: number;
  misfire_grace_seconds: number;
}

export interface TaskDispatchTarget {
  user_id: string;
  session_id: string;
}

export interface TaskDispatch {
  type: "channel";
  channel: string;
  target: TaskDispatchTarget;
  mode: "stream" | "final";
  meta: Record<string, unknown>;
}

export interface TaskRequest {
  input?: unknown;
  session_id?: string;
  user_id?: string;
  [key: string]: unknown;
}

export interface TaskState {
  next_run_at?: string | null;
  last_run_at?: string | null;
  last_status?: "success" | "error" | "running" | "skipped" | "cancelled" | null;
  last_error?: string | null;
}

export interface WebchatTask {
  id?: string | null;
  name: string;
  enabled: boolean;
  schedule: TaskSchedule;
  task_type: "text" | "agent";
  text?: string | null;
  request?: TaskRequest | null;
  dispatch: TaskDispatch;
  runtime: TaskRuntime;
  meta: Record<string, unknown>;
  state?: TaskState;
}

export interface WebchatTaskListResponse {
  tasks: WebchatTask[];
  states: Record<string, TaskState>;
}
