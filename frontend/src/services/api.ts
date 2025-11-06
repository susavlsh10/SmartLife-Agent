const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

interface ApiResponse<T> {
  data?: T
  error?: string
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(error.error || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export const authApi = {
  signup: async (email: string, password: string, name?: string) => {
    return request<{ user: { id: string; email: string; name?: string }; token: string }>(
      '/auth/signup',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, name }),
      }
    )
  },

  login: async (email: string, password: string) => {
    return request<{ user: { id: string; email: string; name?: string }; token: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    )
  },

  verifyToken: async () => {
    return request<{ id: string; email: string; name?: string }>('/auth/verify')
  },
}

export const chatApi = {
  sendMessage: async (message: string) => {
    return request<{ response: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
  },

  getHistory: async () => {
    return request<Array<{ id: string; message: string; response: string; timestamp: string }>>(
      '/chat/history'
    )
  },
}

