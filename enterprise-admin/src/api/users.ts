import { get, patch, post } from "./http"
import type {
  AdminUser,
  CreateAdminUserRequest,
  UpdateAdminUserRequest,
  UserListResponse,
} from "./types"

const USERS_BASE = "/auth/users"

/** 获取管理后台用户列表 */
export function listAdminUsers(): Promise<UserListResponse> {
  return get<UserListResponse>(USERS_BASE)
}

/** 创建管理后台用户 */
export function createAdminUser(payload: CreateAdminUserRequest): Promise<AdminUser> {
  return post<AdminUser>(USERS_BASE, payload)
}

/** 更新管理后台用户（username 会被 encodeURIComponent 编码） */
export function updateAdminUser(
  username: string,
  payload: UpdateAdminUserRequest,
): Promise<AdminUser> {
  return patch<AdminUser>(`${USERS_BASE}/${encodeURIComponent(username)}`, payload)
}
