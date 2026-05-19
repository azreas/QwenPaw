import { apiRequest, setAuthToken } from "../config";

export interface LoginResponse {
  token: string;
  user_id: string;
  username: string;
  agent_id: string;
  employee_id?: string;
}

export interface StatusResponse {
  has_users: boolean;
  auth_mode?: "sso" | string;
}

export interface VerifyResponse {
  valid: boolean;
  user_id: string;
  username: string;
  agent_id: string;
  employee_id?: string;
}

export interface QrcodeConfigResponse {
  enabled: boolean;
  appid?: string;
  agentid?: string;
  redirect_uri?: string;
  state?: string;
  href?: string;
}

function persistLoginResult(result: LoginResponse): void {
  if (result.token) {
    setAuthToken(result.token);
    localStorage.setItem("webchat_user_id", result.user_id);
    localStorage.setItem("webchat_username", result.username);
    localStorage.setItem("webchat_agent_id", result.agent_id);
  }
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const result = await apiRequest<LoginResponse>("/webchat/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    persistLoginResult(result);
    return result;
  },

  async getQrcodeConfig(): Promise<QrcodeConfigResponse> {
    return apiRequest<QrcodeConfigResponse>("/webchat/qrcode/config");
  },

  async loginWithQrcode(code: string, state: string): Promise<LoginResponse> {
    const result = await apiRequest<LoginResponse>("/webchat/login/qrcode", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    });
    persistLoginResult(result);
    return result;
  },

  async status(): Promise<StatusResponse> {
    return apiRequest<StatusResponse>("/webchat/status");
  },

  async verify(): Promise<VerifyResponse> {
    return apiRequest<VerifyResponse>("/webchat/verify", {
      method: "POST",
    });
  },
};
