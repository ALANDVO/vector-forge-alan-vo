import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token')
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Health
  async health() {
    const response = await this.client.get('/health')
    return response.data
  }

  // Sessions
  async listSessions(params?: {
    session_type?: string
    status?: string
    limit?: number
    offset?: number
  }) {
    const response = await this.client.get('/sessions', { params })
    return response.data
  }

  async createSession(data: {
    session_type: string
    target_path: string
    target_hash?: string
    config?: Record<string, unknown>
  }) {
    const response = await this.client.post('/sessions', data)
    return response.data
  }

  async getSession(sessionId: string) {
    const response = await this.client.get(`/sessions/${sessionId}`)
    return response.data
  }

  async updateSessionStatus(sessionId: string, status: string, errorMessage?: string) {
    const response = await this.client.patch(`/sessions/${sessionId}/status`, {
      status,
      error_message: errorMessage,
    })
    return response.data
  }

  // Evidence
  async listEvidence(sessionId: string, params?: {
    evidence_type?: string
    name?: string
    source_file?: string
    limit?: number
    offset?: number
  }) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence`, { params })
    return response.data
  }

  async getEvidence(sessionId: string, evidenceId: string, includeEdges = false) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence/${evidenceId}`, {
      params: { include_edges: includeEdges },
    })
    return response.data
  }

  async searchEvidence(sessionId: string, query: string, params?: {
    evidence_types?: string[]
    limit?: number
  }) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence/search`, {
      params: { query, ...params },
    })
    return response.data
  }

  async getCallers(sessionId: string, evidenceId: string) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence/${evidenceId}/callers`)
    return response.data
  }

  async getCallees(sessionId: string, evidenceId: string) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence/${evidenceId}/callees`)
    return response.data
  }

  async getImports(sessionId: string, evidenceId: string) {
    const response = await this.client.get(`/sessions/${sessionId}/evidence/${evidenceId}/imports`)
    return response.data
  }
  // Generic methods for auth
  async get<T = any>(url: string, config?: any) {
    const response = await this.client.get<T>(url, config)
    return response
  }

  async post<T = any>(url: string, data?: any, config?: any) {
    const response = await this.client.post<T>(url, data, config)
    return response
  }
  async exportSession(sessionId: string) {
    const response = await this.client.get(`/sessions/${sessionId}/export`, {
      responseType: 'blob',
    })
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient