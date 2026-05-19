import { apiRequest } from "../config";
import type { WebchatCapabilitiesResponse } from "../types/capabilities";

export const capabilitiesApi = {
  get: () =>
    apiRequest<WebchatCapabilitiesResponse>("/webchat/capabilities"),
};
