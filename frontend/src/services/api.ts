const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token')
  const headers = new Headers(options.headers as HeadersInit | undefined)

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
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

export interface ProposedProject {
  title: string
  description: string
  due_date?: string | null
}

export interface ChatResponse {
  response: string
  proposed_projects?: ProposedProject[]
  requires_confirmation?: boolean
}

export const chatApi = {
  sendMessage: async (message: string, existingProjects?: ProposedProject[]) => {
    return request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ 
        message,
        existing_projects: existingProjects || undefined
      }),
    })
  },

  getHistory: async () => {
    return request<Array<{ id: string; message: string; response: string; timestamp: string }>>(
      '/chat/history'
    )
  },
}

export interface TodoItem {
  id: string
  text: string
  completed: boolean
  order_index?: string
  created_at: string
}

export interface Project {
  id: string
  title: string
  description?: string
  due_date?: string
  created_at: string
  updated_at: string
  todos: TodoItem[]
}

export interface ProjectChatMessage {
  id: string
  message: string
  response: string
  timestamp: string
}

export const projectsApi = {
  getAll: async () => {
    return request<Project[]>('/projects')
  },

  create: async (data: { title: string; description?: string; due_date?: string }) => {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  get: async (projectId: string) => {
    return request<Project>(`/projects/${projectId}`)
  },

  update: async (projectId: string, data: { title?: string; description?: string; due_date?: string }) => {
    return request<Project>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete: async (projectId: string) => {
    return request<void>(`/projects/${projectId}`, {
      method: 'DELETE',
    })
  },

  addTodo: async (projectId: string, text: string) => {
    return request<TodoItem>(`/projects/${projectId}/todos`, {
      method: 'POST',
      body: JSON.stringify({ text, completed: false }),
    })
  },

  updateTodo: async (projectId: string, todoId: string, data: { text?: string; completed?: boolean }) => {
    return request<TodoItem>(`/projects/${projectId}/todos/${todoId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteTodo: async (projectId: string, todoId: string) => {
    return request<void>(`/projects/${projectId}/todos/${todoId}`, {
      method: 'DELETE',
    })
  },

  sendChatMessage: async (projectId: string, message: string) => {
    return request<{ response: string }>(`/projects/${projectId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
  },

  getChatHistory: async (projectId: string) => {
    return request<ProjectChatMessage[]>(`/projects/${projectId}/chat/history`)
  },
}

export interface TimePreference {
  weekdays?: string
  weekends?: string
  all_time: boolean
}

export interface UserPreferences {
  work_study: TimePreference
  gym_activity: TimePreference
  personal_goals: TimePreference
}

export interface GoogleCalendarStatus {
  connected: boolean
  email?: string
}

export const settingsApi = {
  updatePassword: async (currentPassword: string, newPassword: string) => {
    return request<{ message: string }>('/settings/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
  },

  getGoogleCalendarStatus: async () => {
    return request<GoogleCalendarStatus>('/settings/google-calendar/status')
  },

  getGoogleCalendarAuthUrl: async (redirectUri?: string) => {
    const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''
    return request<{ authorization_url: string; state: string }>(`/settings/google-calendar/authorize${params}`)
  },

  completeGoogleCalendarOAuth: async (code: string, state: string, redirectUri: string) => {
    const params = new URLSearchParams({
      code,
      state,
      redirect_uri: redirectUri,
    })
    return request<{ message: string; email?: string }>(`/settings/google-calendar/callback?${params.toString()}`)
  },

  disconnectGoogleCalendar: async () => {
    return request<{ message: string }>('/settings/google-calendar/disconnect', {
      method: 'DELETE',
    })
  },

  getPreferences: async () => {
    return request<UserPreferences>('/settings/preferences')
  },

  updatePreferences: async (preferences: UserPreferences) => {
    return request<UserPreferences>('/settings/preferences', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    })
  },
}

