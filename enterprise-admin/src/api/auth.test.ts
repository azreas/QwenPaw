import { describe, it, expect, beforeEach, vi } from 'vitest'
import * as authToken from './authToken'

// Use vi.hoisted to solve variable hoisting issue with vi.mock
const { mockRequest } = vi.hoisted(() => {
  return { mockRequest: vi.fn() }
})

vi.mock('axios', () => ({
  default: {
    create: vi.fn().mockReturnValue({
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      request: mockRequest,
    }),
  },
}))

vi.mock('./authToken')

// Import after mocks are set up
import { login, logout, getAuthStatus } from './auth'

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should call post and set token', async () => {
      mockRequest.mockResolvedValue({
        data: { token: 'test-token', username: 'admin', role: 'admin' },
      })

      const result = await login({ username: 'admin', password: 'pass' })

      expect(mockRequest).toHaveBeenCalled()
      expect(authToken.setAuthToken).toHaveBeenCalledWith('test-token')
      expect(result.token).toBe('test-token')
    })
  })

  describe('logout', () => {
    it('should call post and clear token', async () => {
      mockRequest.mockResolvedValue({ data: undefined })

      await logout()

      expect(mockRequest).toHaveBeenCalled()
      expect(authToken.clearAuthToken).toHaveBeenCalled()
    })

    it('should clear token even if post fails', async () => {
      mockRequest.mockRejectedValue(new Error('Network error'))

      await logout()

      expect(authToken.clearAuthToken).toHaveBeenCalled()
    })
  })

  describe('getAuthStatus', () => {
    it('should return authDisabled when auth is not enabled', async () => {
      mockRequest.mockResolvedValue({ data: { enabled: false, has_users: false } })

      const result = await getAuthStatus()

      expect(result).toEqual({ authenticated: false, authDisabled: true })
    })

    it('should return unauthenticated when auth enabled but no token', async () => {
      mockRequest.mockResolvedValue({ data: { enabled: true, has_users: true } })
      vi.mocked(authToken.hasAuthToken).mockReturnValue(false)

      const result = await getAuthStatus()

      expect(result).toEqual({ authenticated: false })
    })

    it('should return auth status when token exists', async () => {
      mockRequest.mockResolvedValueOnce({ data: { enabled: true, has_users: true } })
      mockRequest.mockResolvedValueOnce({ data: { username: 'admin', roles: ['platform_admin'] } })
      vi.mocked(authToken.hasAuthToken).mockReturnValue(true)

      const result = await getAuthStatus()

      expect(result).toEqual({ authenticated: true, username: 'admin', role: 'platform_admin' })
    })

    it('should clear token and return unauthenticated on verify error', async () => {
      mockRequest.mockResolvedValueOnce({ data: { enabled: true, has_users: true } })
      mockRequest.mockRejectedValueOnce(new Error('Unauthorized'))
      vi.mocked(authToken.hasAuthToken).mockReturnValue(true)

      const result = await getAuthStatus()

      expect(authToken.clearAuthToken).toHaveBeenCalled()
      expect(result).toEqual({ authenticated: false })
    })

    it('should return unauthenticated when status endpoint fails', async () => {
      mockRequest.mockRejectedValue(new Error('Network error'))

      const result = await getAuthStatus()

      expect(result).toEqual({ authenticated: false })
    })
  })
})
