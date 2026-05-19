export interface ConsoleUser {
  username: string;
  roles: string[];
  tenant_id: string;
  disabled: boolean;
}

export interface ConsoleUserListResponse {
  items: ConsoleUser[];
}

export interface CreateUserRequest {
  username: string;
  password: string;
  roles?: string[];
  tenant_id?: string;
}

export interface UpdateUserRequest {
  roles?: string[];
  tenant_id?: string;
  disabled?: boolean;
}
