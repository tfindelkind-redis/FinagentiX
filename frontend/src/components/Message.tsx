import { User, Bot } from 'lucide-react'
import { format } from 'date-fns'
import './Message.css'

interface MessageProps {
  message: {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    metrics?: any
  }
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`message ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="message-avatar">
        {isUser ? <User size={20} /> : <Bot size={20} />}
      </div>
      <div className="message-content">
        <div className="message-header">
          <span className="message-role">{isUser ? 'You' : 'Assistant'}</span>
          <span className="message-timestamp">
            {format(message.timestamp, 'HH:mm:ss')}
          </span>
        </div>
        <div className="message-text">{message.content}</div>
      </div>
    </div>
  )
}
