import { getAuthHeaders } from "./config";

export function buildAuthHeaders(): Record<string, string> {
  return getAuthHeaders();
}
