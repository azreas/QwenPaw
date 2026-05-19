export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
