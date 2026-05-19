import { describe, it, expect } from 'vitest'
import { ApiError } from './http'

describe('ApiError', () => {
  it('should create error from axios error', () => {
    const axiosError = {
      response: {
        status: 404,
        data: { message: 'Not found', code: 'NOT_FOUND' },
      },
      message: 'Request failed',
    }

    const error = ApiError.fromAxiosError(axiosError as any)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe('Not found')
    expect(error.status).toBe(404)
    expect(error.code).toBe('NOT_FOUND')
    expect(error.isNotFound()).toBe(true)
    expect(error.isUnauthorized()).toBe(false)
  })

  it('should handle unauthorized error', () => {
    const error = new ApiError('Unauthorized', 401)
    expect(error.isUnauthorized()).toBe(true)
    expect(error.isForbidden()).toBe(false)
  })

  it('should handle forbidden error', () => {
    const error = new ApiError('Forbidden', 403)
    expect(error.isForbidden()).toBe(true)
  })

  it('should handle server error', () => {
    const error = new ApiError('Server error', 500)
    expect(error.isServerError()).toBe(true)
  })
})
