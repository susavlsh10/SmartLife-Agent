import { useState, useRef, useEffect } from 'react'
import { chatApi } from '../services/api'

interface Message {
  id: string
  message: string
  response: string
  timestamp: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadHistory = async () => {
    try {
      const history = await chatApi.getHistory()
      setMessages(history)
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // Add user message optimistically
    const tempId = Date.now().toString()
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        message: userMessage,
        response: '',
        timestamp: new Date().toISOString(),
      },
    ])

    try {
      const { response } = await chatApi.sendMessage(userMessage)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? { ...msg, response, id: `msg-${Date.now()}` }
            : msg
        )
      )
    } catch (error) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? {
                ...msg,
                response: 'Sorry, I encountered an error. Please try again.',
              }
            : msg
        )
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg">Start a conversation</p>
            <p className="text-sm mt-2">Ask me anything!</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="space-y-2">
              <div className="flex justify-end">
                <div className="bg-indigo-600 text-white rounded-lg px-4 py-2 max-w-xs lg:max-w-md">
                  <p className="text-sm">{msg.message}</p>
                </div>
              </div>
              {msg.response && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 text-gray-900 rounded-lg px-4 py-2 max-w-xs lg:max-w-md">
                    <p className="text-sm whitespace-pre-wrap">{msg.response}</p>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-900 rounded-lg px-4 py-2">
              <p className="text-sm">Thinking...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-md border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

