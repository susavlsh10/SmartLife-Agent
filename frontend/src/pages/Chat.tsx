import { useState, useRef, useEffect } from 'react'
import { chatApi, projectsApi, ProposedProject } from '../services/api'

interface EditableProject extends ProposedProject {
  id: string
  selected: boolean
  conversationId: string // Which conversation this project belongs to
}

interface Conversation {
  id: string
  title: string // First message or generated title
  messages: Message[]
  createdAt: string
}

interface Message {
  id: string
  message: string
  response: string
  timestamp: string
  proposedProjects?: EditableProject[]
  requiresConfirmation?: boolean
}

const QUICK_ACTIONS = [
  { text: '🎯 I want to learn a new skill', prompt: 'I want to learn a new skill. Help me identify what I should focus on and create a plan.' },
  { text: '💼 I have career goals', prompt: 'I have some career goals I want to achieve. Help me break them down into actionable projects.' },
  { text: '🏋️ I want to get fit', prompt: 'I want to get fit and improve my health. Create a plan with projects to help me achieve this.' },
  { text: '📚 I want to read more', prompt: 'I want to read more books and expand my knowledge. Help me create a reading project.' },
  { text: '💰 I want to save money', prompt: 'I want to save money and improve my finances. Help me create projects to achieve this goal.' },
  { text: '✈️ I want to travel', prompt: 'I want to plan some travel. Help me create projects to make this happen.' },
]

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [creatingProjects, setCreatingProjects] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const currentConversation = conversations.find(c => c.id === currentConversationId)
  
  // Get all projects from current conversation
  const allProjects: EditableProject[] = currentConversation
    ? currentConversation.messages.flatMap(msg => {
        const projects = msg.proposedProjects || []
        return projects.map(p => ({
          ...p,
          conversationId: currentConversationId || '',
        }))
      })
    : []
  
  const hasProjects = allProjects.length > 0

  // Debug logging
  useEffect(() => {
    if (currentConversation) {
      console.log('Current conversation:', currentConversation)
      console.log('All projects:', allProjects)
      console.log('Has projects:', hasProjects)
    }
  }, [currentConversation, allProjects, hasProjects])

  useEffect(() => {
    scrollToBottom()
  }, [currentConversation?.messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleQuickAction = (prompt: string) => {
    setInput(prompt)
    setTimeout(() => {
      const form = document.querySelector('form') as HTMLFormElement
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))
      }
    }, 100)
  }

  const handleProjectFieldChange = (projectId: string, field: keyof EditableProject, value: string) => {
    if (!currentConversationId) return
    
    setConversations(prev =>
      prev.map(conv =>
        conv.id === currentConversationId
          ? {
              ...conv,
              messages: conv.messages.map(msg => ({
                ...msg,
                proposedProjects: msg.proposedProjects?.map(proj =>
                  proj.id === projectId ? { ...proj, [field]: value } : proj
                ),
              })),
            }
          : conv
      )
    )
  }

  const handleToggleProjectSelection = (projectId: string) => {
    if (!currentConversationId) return
    
    setConversations(prev =>
      prev.map(conv =>
        conv.id === currentConversationId
          ? {
              ...conv,
              messages: conv.messages.map(msg => ({
                ...msg,
                proposedProjects: msg.proposedProjects?.map(proj =>
                  proj.id === projectId ? { ...proj, selected: !proj.selected } : proj
                ),
              })),
            }
          : conv
      )
    )
  }

  const handleMoveSelectedProjects = async () => {
    const selectedProjects = allProjects.filter(p => p.selected)
    if (selectedProjects.length === 0) {
      alert('Please select at least one project to move')
      return
    }

    setCreatingProjects('bulk')
    try {
      const createdProjects = []
      for (const project of selectedProjects) {
        try {
          const created = await projectsApi.create({
            title: project.title,
            description: project.description || undefined,
            due_date: project.due_date || undefined,
          })
          createdProjects.push(created)
        } catch (error) {
          console.error(`Failed to create project "${project.title}":`, error)
        }
      }

      // Remove created projects from proposals
      if (currentConversationId) {
        setConversations(prev =>
          prev.map(conv =>
            conv.id === currentConversationId
              ? {
                  ...conv,
                  messages: conv.messages.map(msg => ({
                    ...msg,
                    proposedProjects: msg.proposedProjects?.filter(p => !p.selected),
                  })),
                }
              : conv
          )
        )
      }

      alert(`✅ Successfully created ${createdProjects.length} project(s)!`)
    } catch (error) {
      console.error('Failed to create projects:', error)
    } finally {
      setCreatingProjects(null)
    }
  }

  const handleEditProjects = async (editPrompt: string) => {
    if (!editPrompt.trim() || !currentConversationId) {
      alert('Please enter an edit request')
      return
    }

    setLoading(true)
    try {
      // Get all current projects for editing
      const currentProjects = allProjects.map(p => ({
        title: p.title,
        description: p.description,
        due_date: p.due_date,
      }))

      const chatResponse = await chatApi.sendMessage(editPrompt, currentProjects)
      
      const newEditableProjects: EditableProject[] = (chatResponse.proposed_projects || []).map((proj, idx) => ({
        ...proj,
        id: `proj-${Date.now()}-${idx}`,
        selected: false,
        conversationId: currentConversationId,
      }))

      // Add new message with updated projects
      const newMessage: Message = {
        id: `msg-${Date.now()}`,
        message: editPrompt,
        response: chatResponse.response,
        timestamp: new Date().toISOString(),
        proposedProjects: newEditableProjects,
        requiresConfirmation: newEditableProjects.length > 0,
      }

      setConversations(prev =>
        prev.map(conv =>
          conv.id === currentConversationId
            ? {
                ...conv,
                messages: [...conv.messages, newMessage],
              }
            : conv
        )
      )
    } catch (error) {
      console.error('Failed to edit projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // Create new conversation if none exists
    let conversationId = currentConversationId
    if (!conversationId) {
      conversationId = `conv-${Date.now()}`
      const newConversation: Conversation = {
        id: conversationId,
        title: userMessage.substring(0, 50),
        messages: [],
        createdAt: new Date().toISOString(),
      }
      setConversations(prev => [...prev, newConversation])
      setCurrentConversationId(conversationId)
    }

    // Add user message optimistically
    const tempId = `msg-${Date.now()}`
    const userMsg: Message = {
      id: tempId,
      message: userMessage,
      response: '',
      timestamp: new Date().toISOString(),
    }

    setConversations(prev =>
      prev.map(conv =>
        conv.id === conversationId
          ? { ...conv, messages: [...conv.messages, userMsg] }
          : conv
      )
    )

    try {
      const chatResponse = await chatApi.sendMessage(userMessage)
      const finalId = `msg-${Date.now()}`
      
      console.log('Chat response:', chatResponse)
      console.log('Proposed projects:', chatResponse.proposed_projects)
      
      const editableProjects: EditableProject[] = (chatResponse.proposed_projects || []).map((proj, idx) => ({
        ...proj,
        id: `proj-${finalId}-${idx}`,
        selected: false,
        conversationId: conversationId!,
      }))
      
      console.log('Editable projects:', editableProjects)
      
      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map(msg =>
                  msg.id === tempId
                    ? {
                        ...msg,
                        id: finalId,
                        response: chatResponse.response,
                        proposedProjects: editableProjects.length > 0 ? editableProjects : undefined,
                        requiresConfirmation: chatResponse.requires_confirmation,
                      }
                    : msg
                ),
              }
            : conv
        )
      )
    } catch (error) {
      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map(msg =>
                  msg.id === tempId
                    ? {
                        ...msg,
                        response: 'Sorry, I encountered an error. Please try again.',
                      }
                    : msg
                ),
              }
            : conv
        )
      )
    } finally {
      setLoading(false)
    }
  }

  const startNewConversation = () => {
    setCurrentConversationId(null)
    setInput('')
  }

  return (
    <div className="flex h-full">
      {/* Sidebar - Chat Interface */}
      <div className={`${currentConversation ? 'w-80 border-r border-gray-200' : 'w-full'} flex flex-col bg-white transition-all duration-300`}>
        {/* Conversation Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Goal Conversations</h2>
          <button
            onClick={startNewConversation}
            className="px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            + New
          </button>
        </div>

        {/* Conversation List */}
        {conversations.length > 0 && (
          <div className="border-b border-gray-200 p-2 overflow-y-auto max-h-32">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => setCurrentConversationId(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm mb-1 ${
                  currentConversationId === conv.id
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <div className="truncate">{conv.title}</div>
                <div className="text-xs text-gray-500">
                  {conv.messages.length} message{conv.messages.length !== 1 ? 's' : ''}
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!currentConversation ? (
            <div className="text-center mt-8">
              <p className="text-xl font-semibold text-gray-800 mb-2">What would you like to accomplish?</p>
              <p className="text-sm text-gray-500 mb-6">Tell me about your goals, or choose a quick start option</p>
              
              <div className="grid grid-cols-1 gap-2 max-w-sm mx-auto">
                {QUICK_ACTIONS.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickAction(action.prompt)}
                    className="text-left bg-white border-2 border-gray-200 rounded-lg px-4 py-2 hover:border-indigo-500 hover:bg-indigo-50 transition-all text-sm font-medium text-gray-700"
                    disabled={loading}
                  >
                    {action.text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {currentConversation.messages.map((msg) => (
                <div key={msg.id} className="space-y-2">
                  <div className="flex justify-end">
                    <div className="bg-indigo-600 text-white rounded-lg px-3 py-2 max-w-[85%]">
                      <p className="text-xs">{msg.message}</p>
                    </div>
                  </div>
                  {msg.response && (
                    <div className="flex justify-start">
                      <div className="bg-gray-200 text-gray-900 rounded-lg px-3 py-2 max-w-[85%]">
                        <p className="text-xs whitespace-pre-wrap">{msg.response}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 text-gray-900 rounded-lg px-3 py-2">
                    <p className="text-xs">Thinking...</p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3 bg-white">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={currentConversation ? "Continue conversation..." : "Share your goals..."}
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 text-sm"
            >
              Send
            </button>
          </div>
        </form>
      </div>

      {/* Main Area - Project Proposals */}
      {currentConversation && (
        <div className="flex-1 flex flex-col bg-gray-50">
          <div className="p-6 border-b border-gray-200 bg-white">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Project Proposals</h2>
            <p className="text-sm text-gray-600">
              {hasProjects 
                ? 'Review and edit your project ideas. Select the ones you want to add to your projects.'
                : 'Project proposals will appear here once generated.'}
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {allProjects.length === 0 ? (
              <div className="text-center mt-12 text-gray-500">
                <p className="text-lg mb-2">No project proposals yet.</p>
                <p className="text-sm">Continue the conversation to generate project ideas!</p>
              </div>
            ) : (
              <div className="space-y-4 max-w-4xl mx-auto">
                {allProjects.map((project) => (
                  <div
                    key={project.id}
                    className={`bg-white rounded-lg p-4 border-2 transition-all ${
                      project.selected ? 'border-indigo-500 bg-indigo-50 shadow-md' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <input
                        type="checkbox"
                        checked={project.selected || false}
                        onChange={() => handleToggleProjectSelection(project.id)}
                        className="mt-1 h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                      />
                      <div className="flex-1 space-y-3">
                        <input
                          type="text"
                          value={project.title || ''}
                          onChange={(e) => handleProjectFieldChange(project.id, 'title', e.target.value)}
                          className="w-full text-lg font-semibold text-gray-900 border-b-2 border-transparent hover:border-gray-300 focus:border-indigo-500 focus:outline-none px-2 py-1 transition-colors"
                          placeholder="Project title"
                        />
                        <textarea
                          value={project.description || ''}
                          onChange={(e) => handleProjectFieldChange(project.id, 'description', e.target.value)}
                          className="w-full text-sm text-gray-700 border border-gray-300 rounded-lg px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
                          placeholder="Project description (optional)"
                          rows={3}
                        />
                        <div className="flex items-center gap-3">
                          <label className="text-sm font-medium text-gray-700">Due Date:</label>
                          <input
                            type="date"
                            value={project.due_date || ''}
                            onChange={(e) => handleProjectFieldChange(project.id, 'due_date', e.target.value)}
                            className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Bar */}
          {allProjects.length > 0 && (
            <div className="border-t border-gray-200 p-4 bg-white">
              <div className="max-w-4xl mx-auto flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  {allProjects.filter(p => p.selected).length} of {allProjects.length} selected
                </div>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="Ask for changes (e.g., 'Make due dates later')"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        const input = e.currentTarget as HTMLInputElement
                        if (input.value.trim()) {
                          handleEditProjects(input.value)
                          input.value = ''
                        }
                      }
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
                  />
                  <button
                    onClick={handleMoveSelectedProjects}
                    disabled={creatingProjects === 'bulk' || !allProjects.some(p => p.selected)}
                    className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                  >
                    {creatingProjects === 'bulk'
                      ? 'Creating...'
                      : `📦 Move ${allProjects.filter(p => p.selected).length} Selected to Projects`}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
