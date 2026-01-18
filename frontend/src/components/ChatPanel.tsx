import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import MessageList from './MessageList'
import LearnMode from './LearnMode'
import type { EnhancedQueryResponse } from '@/types/api'
import './ChatPanel.css'

// Maximum number of message pairs to keep visible
const MAX_VISIBLE_MESSAGES = 20

interface ChatPanelProps {
  sessionId: string
  onResponseReceived: (response: EnhancedQueryResponse) => void
  onClearHistory?: () => void
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metrics?: EnhancedQueryResponse
}

export default function ChatPanel({ sessionId, onResponseReceived, onClearHistory }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  const queryMutation = useMutation({
    mutationFn: api.query.executeEnhanced,
    onSuccess: (data) => {
      // Add assistant message
      const assistantMessage: Message = {
        id: data.query_id,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(data.timestamp),
        metrics: data,
      }
      setMessages((prev) => [...prev, assistantMessage])
      onResponseReceived(data)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || queryMutation.isPending) return

    // Add user message
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Execute query
    queryMutation.mutate({
      query: input,
      user_id: sessionId,
    })

    setInput('')
  }

  // Keep only the most recent messages for display
  const visibleMessages = messages.slice(-MAX_VISIBLE_MESSAGES)
  const hiddenCount = messages.length - visibleMessages.length

  const handleClearHistory = () => {
    setMessages([])
    onClearHistory?.()
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Chat</h2>
        <div className="chat-header-actions">
          <span className="message-count">{messages.length} messages</span>
          {messages.length > 0 && (
            <button 
              className="clear-history-btn" 
              onClick={handleClearHistory}
              title="Clear chat history"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      <MessageList 
        messages={visibleMessages} 
        isLoading={queryMutation.isPending}
        hiddenCount={hiddenCount}
      />

      <LearnMode 
        onSelectQuestion={(question) => setInput(question)}
        isDisabled={queryMutation.isPending}
      />

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about stocks, portfolios, or market analysis..."
          className="chat-input"
          disabled={queryMutation.isPending}
        />
        <button
          type="submit"
          className="chat-submit"
          disabled={!input.trim() || queryMutation.isPending}
        >
          <Send size={20} />
        </button>
      </form>

      {queryMutation.isError && (
        <div className="chat-error">
          Error: {queryMutation.error?.message || 'Failed to process query'}
        </div>
      )}
    </div>
  )
}
