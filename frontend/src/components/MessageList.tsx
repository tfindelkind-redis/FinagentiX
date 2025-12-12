import { useEffect, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import Message from './Message'
import './MessageList.css'

interface MessageData {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metrics?: any
}

interface MessageListProps {
  messages: MessageData[]
  isLoading: boolean
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  return (
    <div className="message-list" ref={scrollRef}>
      {messages.length === 0 ? (
        <div className="empty-state">
          <h3>Welcome to FinagentiX</h3>
          <p>Ask me anything about stocks, portfolios, or market analysis.</p>
        </div>
      ) : (
        messages.map((message) => (
          <Message key={message.id} message={message} />
        ))
      )}

      {isLoading && (
        <div className="loading-indicator">
          <Loader2 size={20} className="spinner" />
          <span>Thinking...</span>
        </div>
      )}
    </div>
  )
}
