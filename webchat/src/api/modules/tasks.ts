import { apiRequest } from "../config";
import type { WebchatTask, WebchatTaskListResponse } from "../types/tasks";

type TaskListPayload = WebchatTaskListResponse | WebchatTask[];

function normalizeTaskList(payload: TaskListPayload): WebchatTask[] {
  if (Array.isArray(payload)) return payload;

  return payload.tasks.map((task) => {
    if (!task.id) return task;
    return {
      ...task,
      state: payload.states[task.id] ?? task.state,
    };
  });
}

export const tasksApi = {
  list: async (): Promise<WebchatTask[]> => {
    const payload = await apiRequest<TaskListPayload>("/webchat/tasks");
    return normalizeTaskList(payload);
  },

  create: (task: WebchatTask) =>
    apiRequest<WebchatTask>("/webchat/tasks", {
      method: "POST",
      body: JSON.stringify(task),
    }),

  update: (taskId: string, task: WebchatTask) =>
    apiRequest<WebchatTask>(`/webchat/tasks/${encodeURIComponent(taskId)}`, {
      method: "PUT",
      body: JSON.stringify(task),
    }),

  remove: (taskId: string) =>
    apiRequest<{ deleted: boolean }>(
      `/webchat/tasks/${encodeURIComponent(taskId)}`,
      {
        method: "DELETE",
      }
    ),

  pause: (taskId: string) =>
    apiRequest<{ paused: boolean }>(
      `/webchat/tasks/${encodeURIComponent(taskId)}/pause`,
      {
        method: "POST",
      }
    ),

  resume: (taskId: string) =>
    apiRequest<{ resumed: boolean }>(
      `/webchat/tasks/${encodeURIComponent(taskId)}/resume`,
      {
        method: "POST",
      }
    ),

  run: (taskId: string) =>
    apiRequest<{ started: boolean }>(
      `/webchat/tasks/${encodeURIComponent(taskId)}/run`,
      {
        method: "POST",
      }
    ),
};
