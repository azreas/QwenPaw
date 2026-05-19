import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react"
import { login, logout, getAuthStatus } from "@/api/auth"
import { clearAuthToken } from "@/api/authToken"
import type { AuthStatus, LoginRequest, LoginResponse } from "@/api/types"

export interface AuthContextType {
  isAuthenticated: boolean
  user: AuthStatus | null
  loading: boolean
  login: (credentials: LoginRequest) => Promise<LoginResponse>
  logout: () => Promise<void>
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<{
    isAuthenticated: boolean
    user: AuthStatus | null
    loading: boolean
  }>({
    isAuthenticated: false,
    user: null,
    loading: true,
  })

  const refreshAuth = useCallback(async () => {
    try {
      const status = await getAuthStatus()
      setAuthState({
        isAuthenticated: status.authenticated || status.authDisabled === true,
        user: status,
        loading: false,
      })
    } catch (error) {
      clearAuthToken()
      setAuthState({
        isAuthenticated: false,
        user: null,
        loading: false,
      })
    }
  }, [])

  useEffect(() => {
    refreshAuth()
  }, [refreshAuth])

  const handleLogin = useCallback(async (credentials: LoginRequest) => {
    const response = await login(credentials)
    await refreshAuth()
    return response
  }, [refreshAuth])

  const handleLogout = useCallback(async () => {
    await logout()
    setAuthState({
      isAuthenticated: false,
      user: null,
      loading: false,
    })
  }, [])

  const value: AuthContextType = {
    isAuthenticated: authState.isAuthenticated,
    user: authState.user,
    loading: authState.loading,
    login: handleLogin,
    logout: handleLogout,
    refreshAuth,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
