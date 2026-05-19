import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios'
import { API_BASE_URL } from './config'
import { getAuthToken, clearAuthToken } from './authToken'

export class ApiError extends Error {
  public readonly status: number
  public readonly code?: string
  public readonly details?: unknown

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  public static fromAxiosError(error: AxiosError): ApiError {
    const status = error.response?.status ?? 500
    const message = (error.response?.data as { message?: string })?.message ?? error.message
    const code = (error.response?.data as { code?: string })?.code
    const details = error.response?.data

    return new ApiError(message, status, code, details)
  }

  public isUnauthorized(): boolean {
    return this.status === 401
  }

  public isForbidden(): boolean {
    return this.status === 403
  }

  public isNotFound(): boolean {
    return this.status === 404
  }

  public isServerError(): boolean {
    return this.status >= 500
  }
}

function createAxiosInstance(baseURL: string): AxiosInstance {
  const instance = axios.create({ baseURL })

  instance.interceptors.request.use((config) => {
    const token = getAuthToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      const apiError = ApiError.fromAxiosError(error)

      if (apiError.isUnauthorized()) {
        clearAuthToken()
      }

      return Promise.reject(apiError)
    },
  )

  return instance
}

const apiInstance = createAxiosInstance(API_BASE_URL)
const rootInstance = createAxiosInstance('/')

export async function request<T = unknown>(
  config: AxiosRequestConfig,
): Promise<T> {
  const response = await apiInstance.request<T>(config)
  return response.data
}

export async function rootRequest<T = unknown>(
  config: AxiosRequestConfig,
): Promise<T> {
  const response = await rootInstance.request<T>(config)
  return response.data
}

export async function get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'GET', url, ...config })
}

export async function getRoot<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return rootRequest<T>({ method: 'GET', url, ...config })
}

export async function post<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ method: 'POST', url, data, ...config })
}

export async function put<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ method: 'PUT', url, data, ...config })
}

export async function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ method: 'DELETE', url, ...config })
}

export async function patch<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ method: 'PATCH', url, data, ...config })
}
