import { useState, useEffect, useRef } from 'react'
import { projectsApi, Project, TodoItem, ProjectChatMessage } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function Home() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)
  
  const [projectTitle, setProjectTitle] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [projectDueDate, setProjectDueDate] = useState('')
  const [newTodoText, setNewTodoText] = useState('')
  
  const [chatMessages, setChatMessages] = useState<ProjectChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      loadProjectDetails()
      loadChatHistory()
    }
  }, [selectedProject?.id])

  useEffect(() => {
    scrollToBottom()
  }, [chatMessages])

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadProjects = async () => {
    try {
      const data = await projectsApi.getAll()
      setProjects(data)
      if (data.length > 0 && !selectedProject) {
        setSelectedProject(data[0])
      }
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadProjectDetails = async () => {
    if (!selectedProject) return
    try {
      const data = await projectsApi.get(selectedProject.id)
      setSelectedProject(data)
      setProjects(prev => prev.map(p => p.id === data.id ? data : p))
    } catch (error) {
      console.error('Failed to load project details:', error)
    }
  }

  const loadChatHistory = async () => {
    if (!selectedProject) return
    try {
      const history = await projectsApi.getChatHistory(selectedProject.id)
      setChatMessages(history)
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projectTitle.trim()) return

    setLoading(true)
    try {
      const newProject = await projectsApi.create({
        title: projectTitle,
        description: projectDescription,
        due_date: projectDueDate || undefined,
      })
      setProjects(prev => [newProject, ...prev])
      setSelectedProject(newProject)
      setShowNewProjectModal(false)
      setProjectTitle('')
      setProjectDescription('')
      setProjectDueDate('')
    } catch (error) {
      console.error('Failed to create project:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateProject = async () => {
    if (!selectedProject) return
    try {
      const updated = await projectsApi.update(selectedProject.id, {
        title: selectedProject.title,
        description: selectedProject.description,
        due_date: selectedProject.due_date,
      })
      setSelectedProject(updated)
      setProjects(prev => prev.map(p => p.id === updated.id ? updated : p))
    } catch (error) {
      console.error('Failed to update project:', error)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return
    
    try {
      await projectsApi.delete(projectId)
      setProjects(prev => prev.filter(p => p.id !== projectId))
      if (selectedProject?.id === projectId) {
        setSelectedProject(projects.find(p => p.id !== projectId) || null)
      }
    } catch (error) {
      console.error('Failed to delete project:', error)
    }
  }

  const handleAddTodo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProject || !newTodoText.trim()) return

    try {
      const newTodo = await projectsApi.addTodo(selectedProject.id, newTodoText)
      setSelectedProject({
        ...selectedProject,
        todos: [...selectedProject.todos, newTodo],
      })
      setNewTodoText('')
    } catch (error) {
      console.error('Failed to add todo:', error)
    }
  }

  const handleToggleTodo = async (todo: TodoItem) => {
    if (!selectedProject) return

    try {
      const updated = await projectsApi.updateTodo(selectedProject.id, todo.id, {
        completed: !todo.completed,
      })
      setSelectedProject({
        ...selectedProject,
        todos: selectedProject.todos.map(t => t.id === todo.id ? updated : t),
      })
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const handleDeleteTodo = async (todoId: string) => {
    if (!selectedProject) return

    try {
      await projectsApi.deleteTodo(selectedProject.id, todoId)
      setSelectedProject({
        ...selectedProject,
        todos: selectedProject.todos.filter(t => t.id !== todoId),
      })
    } catch (error) {
      console.error('Failed to delete todo:', error)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProject || !chatInput.trim() || chatLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setChatLoading(true)

    const tempMessage: ProjectChatMessage = {
      id: `temp-${Date.now()}`,
      message: userMessage,
      response: '',
      timestamp: new Date().toISOString(),
    }
    setChatMessages(prev => [...prev, tempMessage])

    try {
      const { response } = await projectsApi.sendChatMessage(selectedProject.id, userMessage)
      setChatMessages(prev =>
        prev.map(msg =>
          msg.id === tempMessage.id
            ? { ...msg, response, id: `msg-${Date.now()}` }
            : msg
        )
      )
    } catch (error) {
      setChatMessages(prev =>
        prev.map(msg =>
          msg.id === tempMessage.id
            ? { ...msg, response: 'Sorry, I encountered an error. Please try again.' }
            : msg
        )
      )
    } finally {
      setChatLoading(false)
    }
  }

  const handleClearChat = () => {
    if (window.confirm('Clear chat history for this project? This cannot be undone.')) {
      setChatMessages([])
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-8">
              <h1 className="text-xl font-semibold text-gray-900">SmartLife Agent</h1>
              <div className="flex space-x-2">
                <button className="px-4 py-2 rounded-md text-sm font-medium bg-indigo-100 text-indigo-700">
                  Projects
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100"
                >
                  General Chat
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">{user?.name || user?.email}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md hover:bg-gray-100"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800">Your Projects</h2>
            <p className="text-gray-600 mt-1 text-sm">Manage and organize your work</p>
          </div>

          <div className="p-4 border-b border-gray-200">
            <button
              onClick={() => setShowNewProjectModal(true)}
              className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 transition-colors font-medium flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Project
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">All Projects</h3>
            <div className="space-y-2">
              {projects.map(project => (
                <div
                  key={project.id}
                  className={`group relative p-3 rounded-lg cursor-pointer transition-all ${
                    selectedProject?.id === project.id
                      ? 'bg-indigo-50 border-2 border-indigo-200'
                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                  }`}
                  onClick={() => setSelectedProject(project)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">{project.title}</h4>
                      {project.due_date && (
                        <p className="text-xs text-gray-500 mt-1">
                          Due: {new Date(project.due_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteProject(project.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700 p-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    {project.todos.filter(t => t.completed).length}/{project.todos.length} tasks completed
                  </div>
                </div>
              ))}
              {projects.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">
                  No projects yet. Create your first project!
                </p>
              )}
            </div>
          </div>
        </div>

        {selectedProject ? (
          <div className="flex-1 flex">
            <div className="flex-1 flex flex-col bg-white border-r border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <input
                  type="text"
                  value={selectedProject.title}
                  onChange={(e) => setSelectedProject({ ...selectedProject, title: e.target.value })}
                  onBlur={handleUpdateProject}
                  className="text-3xl font-bold text-gray-900 w-full border-none focus:outline-none focus:ring-0 p-0"
                  placeholder="Project Title"
                />
              </div>

              <div className="flex-1 overflow-y-auto p-6">
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
                  <textarea
                    value={selectedProject.description || ''}
                    onChange={(e) => setSelectedProject({ ...selectedProject, description: e.target.value })}
                    onBlur={handleUpdateProject}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                    rows={4}
                    placeholder="Enter project description..."
                  />
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Due Date</label>
                  <input
                    type="date"
                    value={selectedProject.due_date ? selectedProject.due_date.split('T')[0] : ''}
                    onChange={(e) => setSelectedProject({ ...selectedProject, due_date: e.target.value ? new Date(e.target.value).toISOString() : undefined })}
                    onBlur={handleUpdateProject}
                    className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">Todo List</label>
                  <div className="space-y-2 mb-4">
                    {selectedProject.todos.map(todo => (
                      <div
                        key={todo.id}
                        className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                      >
                        <input
                          type="checkbox"
                          checked={todo.completed}
                          onChange={() => handleToggleTodo(todo)}
                          className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer"
                        />
                        <span className={`flex-1 ${todo.completed ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                          {todo.text}
                        </span>
                        <button
                          onClick={() => handleDeleteTodo(todo.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                  <form onSubmit={handleAddTodo} className="flex gap-2">
                    <input
                      type="text"
                      value={newTodoText}
                      onChange={(e) => setNewTodoText(e.target.value)}
                      placeholder="Add a new task..."
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    <button
                      type="submit"
                      className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                    >
                      Add
                    </button>
                  </form>
                </div>
              </div>
            </div>

            <div className="w-96 flex flex-col bg-gray-50">
              <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">AI Assistant</h3>
                  <p className="text-sm text-gray-600 mt-1">Get help planning your project</p>
                </div>
                {chatMessages.length > 0 && (
                  <button
                    onClick={handleClearChat}
                    className="text-sm text-gray-600 hover:text-red-600 px-3 py-2 rounded-md hover:bg-gray-100 transition-colors flex items-center gap-2"
                    title="Clear chat history"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    <span>Clear</span>
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center text-gray-500 mt-8">
                    <svg className="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                    <p className="text-sm">Ask the AI assistant for help with:</p>
                    <ul className="text-sm mt-2 text-left inline-block">
                      <li>• Breaking down tasks</li>
                      <li>• Setting priorities</li>
                      <li>• Planning timelines</li>
                      <li>• Project suggestions</li>
                    </ul>
                  </div>
                ) : (
                  chatMessages.map(msg => (
                    <div key={msg.id} className="space-y-2">
                      <div className="flex justify-end">
                        <div className="bg-indigo-600 text-white rounded-lg px-4 py-2 max-w-[85%]">
                          <p className="text-sm">{msg.message}</p>
                        </div>
                      </div>
                      {msg.response && (
                        <div className="flex justify-start">
                          <div className="bg-white text-gray-900 rounded-lg px-4 py-2 max-w-[85%] shadow-sm border border-gray-200">
                            <div className="text-sm prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.response}
                              </ReactMarkdown>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="p-4 bg-white border-t border-gray-200">
                <form onSubmit={handleSendMessage} className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask for help..."
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    disabled={chatLoading || !chatInput.trim()}
                    className="bg-indigo-600 text-white px-4 py-3 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </form>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-white">
            <div className="text-center text-gray-500">
              <svg className="w-20 h-20 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-xl font-medium">Select a project to get started</p>
              <p className="text-sm mt-2">or create a new one</p>
            </div>
          </div>
        )}
      </div>

      {showNewProjectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900">Create New Project</h2>
            </div>
            <form onSubmit={handleCreateProject} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Project Title *</label>
                <input
                  type="text"
                  value={projectTitle}
                  onChange={(e) => setProjectTitle(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter project title"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                  rows={3}
                  placeholder="Enter project description"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Due Date</label>
                <input
                  type="date"
                  value={projectDueDate}
                  onChange={(e) => setProjectDueDate(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowNewProjectModal(false)
                    setProjectTitle('')
                    setProjectDescription('')
                    setProjectDueDate('')
                  }}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !projectTitle.trim()}
                  className="flex-1 bg-indigo-600 text-white px-4 py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
