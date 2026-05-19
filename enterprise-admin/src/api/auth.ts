import { post, get } from './http'
import { setAuthToken, clearAuthToken, hasAuthToken } from './authToken'
import type { AuthStatus, LoginRequest, LoginResponse } from './types'

interface BackendAuthStatus {
  enabled: boolean
  has_users: boolean
}

interface VerifyResponse {
  username: string
  roles?: string[]
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await post<LoginResponse>('/auth/login', credentials)
  setAuthToken(response.token)
  return response
}

export async function logout(): Promise<void> {
  try {
    await post('/auth/logout')
  } catch {
    // Ignore errors - we still want to clear the token locally
  } finally {
    clearAuthToken()
  }
}

export async function getAuthStatus(): Promise<AuthStatus> {
  // 先检查认证是否启用；未启用时直接放行
  try {
    const status = await get<BackendAuthStatus>('/auth/status')
    if (!status.enabled) {
      return { authenticated: false, authDisabled: true }
    }
  } catch {
    // 如果 /auth/status 都请求失败，视为未认证
    return { authenticated: false }
  }

  if (!hasAuthToken()) {
    return { authenticated: false }
  }

  try {
    const verify = await get<VerifyResponse>('/auth/verify')
    return {
      authenticated: true,
      username: verify.username,
      role: verify.roles?.[0],
    }
  } catch {
    clearAuthToken()
    return { authenticated: false }
  }
}
