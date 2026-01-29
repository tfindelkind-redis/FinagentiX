import { useState, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Trash2, Zap } from 'lucide-react'
import { api, executeQueryStream, type StreamEvent, type AgentSpec } from '@/lib/api'
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

interface AgentProgress {
  id: string
  name: string
  icon: string
  status: 'pending' | 'running' | 'done'
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metrics?: EnhancedQueryResponse
  isStreaming?: boolean
  agentProgress?: AgentProgress[]
}

// Simple metrics collected during streaming
interface StreamingMetrics {
  agents_used?: string[]
  processing_time_ms?: number
  confidence_score?: number
  recommendation?: string | null
  ticker?: string | null
  query_id?: string
}

export default function ChatPanel({ sessionId, onResponseReceived, onClearHistory }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [useStreaming, setUseStreaming] = useState(true)
  const [isStreaming, setIsStreaming] = useState(false)
  const streamContentRef = useRef<string>('')
  const streamMetricsRef = useRef<StreamingMetrics>({})
  const agentProgressRef = useRef<AgentProgress[]>([])

  // Non-streaming mutation (fallback)
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

  // Handle streaming events
  const handleStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case 'status':
        // Could show status updates in UI
        console.log('Stream status:', event.message)
        break
      
      case 'agents_init':
        // Initialize agent progress list
        if (event.agents) {
          agentProgressRef.current = event.agents.map((a: AgentSpec) => ({
            id: a.id,
            name: a.name,
            icon: a.icon,
            status: 'pending' as const,
          }))
          // Update message with agent progress
          setMessages((prev) => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
              updated[lastIdx] = {
                ...updated[lastIdx],
                agentProgress: [...agentProgressRef.current],
              }
            }
            return updated
          })
        }
        break
      
      case 'agent_start':
        // Mark agent as running
        if (event.agent_id !== undefined) {
          const idx = agentProgressRef.current.findIndex(a => a.id === event.agent_id)
          if (idx >= 0) {
            agentProgressRef.current[idx].status = 'running'
            setMessages((prev) => {
              const updated = [...prev]
              const lastIdx = updated.length - 1
              if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  agentProgress: [...agentProgressRef.current],
                }
              }
              return updated
            })
          }
        }
        break
      
      case 'agent_done':
        // Mark agent as done
        if (event.agent_id !== undefined) {
          const idx = agentProgressRef.current.findIndex(a => a.id === event.agent_id)
          if (idx >= 0) {
            agentProgressRef.current[idx].status = 'done'
            setMessages((prev) => {
              const updated = [...prev]
              const lastIdx = updated.length - 1
              if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  agentProgress: [...agentProgressRef.current],
                }
              }
              return updated
            })
          }
        }
        break
      
      case 'agent_data':
        // Store agent data for final metrics
        streamMetricsRef.current = {
          ...streamMetricsRef.current,
          agents_used: event.agents_used,
          processing_time_ms: event.processing_time_ms,
          ticker: event.ticker,
          confidence_score: event.confidence_score,
        }
        break
      
      case 'recommendation':
        // Store recommendation
        streamMetricsRef.current.recommendation = event.recommendation
        break
      
      case 'llm_start':
        // LLM is starting to generate - clear agent progress display
        console.log('LLM starting synthesis...')
        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.length - 1
          if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              agentProgress: undefined, // Hide agent progress, show content
            }
          }
          return updated
        })
        break
      
      case 'llm_chunk':
        // Append chunk to content
        streamContentRef.current += event.content || ''
        // Update the streaming message with new content
        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.length - 1
          if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: streamContentRef.current,
            }
          }
          return updated
        })
        break
      
      case 'llm_done':
        // LLM finished
        console.log('LLM synthesis complete')
        break
      
      case 'done':
        // Stream complete - finalize message
        streamMetricsRef.current.query_id = event.query_id
        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.length - 1
          if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
            updated[lastIdx] = {
              ...updated[lastIdx],
              isStreaming: false,
              agentProgress: undefined,
              // Note: metrics will be partial for streaming responses
            }
          }
          return updated
        })
        setIsStreaming(false)
        break
      
      case 'cache_hit':
        // Cache hit - show cached response immediately
        if (event.response) {
          streamContentRef.current = event.response
          setMessages((prev) => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: event.response || '',
                isStreaming: false,
                agentProgress: undefined,
              }
            }
            return updated
          })
          setIsStreaming(false)
        }
        break
      
      case 'error':
        console.error('Stream error:', event.message)
        setIsStreaming(false)
        break
    }
  }, [])

  // Streaming submit handler
  const handleStreamingSubmit = async (query: string) => {
    setIsStreaming(true)
    streamContentRef.current = ''
    streamMetricsRef.current = {}
    agentProgressRef.current = []

    // Add placeholder assistant message that will be updated
    const streamingMessage: Message = {
      id: `stream_${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    }
    setMessages((prev) => [...prev, streamingMessage])

    try {
      await executeQueryStream(
        { query, user_id: sessionId },
        handleStreamEvent
      )
    } catch (error) {
      console.error('Streaming error:', error)
      setIsStreaming(false)
      // Update message to show error
      setMessages((prev) => {
        const updated = [...prev]
        const lastIdx = updated.length - 1
        if (lastIdx >= 0 && updated[lastIdx].isStreaming) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: 'Error: Failed to get streaming response. Please try again.',
            isStreaming: false,
            agentProgress: undefined,
          }
        }
        return updated
      })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || queryMutation.isPending || isStreaming) return

    // Add user message
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    const query = input
    setInput('')

    if (useStreaming) {
      // Use streaming
      handleStreamingSubmit(query)
    } else {
      // Use traditional mutation
      queryMutation.mutate({
        query,
        user_id: sessionId,
      })
    }
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
          <button
            className={`streaming-toggle ${useStreaming ? 'active' : ''}`}
            onClick={() => setUseStreaming(!useStreaming)}
            title={useStreaming ? 'Streaming enabled (shows response as it generates)' : 'Streaming disabled'}
          >
            <Zap size={14} />
            <span>Stream</span>
          </button>
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
        isLoading={queryMutation.isPending || isStreaming}
        hiddenCount={hiddenCount}
      />

      <LearnMode 
        onSelectQuestion={(question) => setInput(question)}
        isDisabled={queryMutation.isPending || isStreaming}
      />

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about stocks, portfolios, or market analysis..."
          className="chat-input"
          disabled={queryMutation.isPending || isStreaming}
        />
        <button
          type="submit"
          className="chat-submit"
          disabled={!input.trim() || queryMutation.isPending || isStreaming}
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
