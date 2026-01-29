import { User, Bot, CheckCircle, Loader2 } from 'lucide-react'
import { format } from 'date-fns'
import './Message.css'

interface AgentProgress {
  id: string
  name: string
  icon: string
  status: 'pending' | 'running' | 'done'
}

interface MessageProps {
  message: {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    metrics?: any
    isStreaming?: boolean
    agentProgress?: AgentProgress[]
  }
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user'
  const showAgentProgress = !isUser && message.isStreaming && message.agentProgress && message.agentProgress.length > 0

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
        
        {showAgentProgress ? (
          <div className="agent-progress">
            <div className="agent-progress-label">Researching...</div>
            <div className="agent-progress-list">
              {message.agentProgress!.map((agent) => (
                <div 
                  key={agent.id} 
                  className={`agent-progress-item agent-status-${agent.status}`}
                  title={agent.name}
                >
                  <span className="agent-icon">{agent.icon}</span>
                  {agent.status === 'running' && (
                    <Loader2 size={12} className="agent-spinner" />
                  )}
                  {agent.status === 'done' && (
                    <CheckCircle size={12} className="agent-check" />
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-text">
            {message.content || (message.isStreaming ? '...' : '')}
            {message.isStreaming && message.content && (
              <span className="streaming-cursor">▋</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
