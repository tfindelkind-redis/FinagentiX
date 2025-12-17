import { useState } from 'react'
import { Info, Zap, Database, Clock, DollarSign, ChevronDown, CheckCircle, AlertCircle, Sparkles } from 'lucide-react'
import { AGENT_EXPLANATIONS } from '@/data/learnModeQuestions'
import type { EnhancedQueryResponse } from '@/types/api'
import './AgentsTab.css'

interface AgentsTabProps {
  response: EnhancedQueryResponse
}

export default function AgentsTab({ response }: AgentsTabProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [showExplanations, setShowExplanations] = useState(true)

  const toggleAgent = (agentId: string) => {
    setExpandedAgent(expandedAgent === agentId ? null : agentId)
  }

  // Show cached response state when no agents
  if (response.agents.length === 0) {
    return (
      <div className="agents-tab">
        <div className="agents-header">
          <h3>Execution Details</h3>
        </div>
        
        <div className="cached-response-info">
          <div className="cached-icon">
            <Sparkles size={48} />
          </div>
          <h4>⚡ Instant Response from Cache</h4>
          <p>This query was served directly from the semantic cache - no agents were needed!</p>
          
          <div className="cache-benefits">
            <div className="cache-benefit">
              <Database size={16} />
              <span>Semantic similarity matched a previous query</span>
            </div>
            <div className="cache-benefit">
              <Clock size={16} />
              <span>Response time: {response.performance.total_time_ms.toFixed(0)}ms</span>
            </div>
            <div className="cache-benefit">
              <DollarSign size={16} />
              <span>Cost saved: ${response.cost.cost_savings_usd.toFixed(4)}</span>
            </div>
          </div>
          
          {response.cache_layers.find(l => l.hit)?.matched_query && (
            <div className="matched-query">
              <strong>Matched query:</strong>
              <p>"{response.cache_layers.find(l => l.hit)?.matched_query}"</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="agents-tab">
      <div className="agents-header">
        <h3>Agent Execution Details</h3>
        <label className="explanation-toggle">
          <input 
            type="checkbox" 
            checked={showExplanations} 
            onChange={(e) => setShowExplanations(e.target.checked)}
          />
          <span>Show Redis Benefits</span>
          <Info size={14} />
        </label>
      </div>

      {/* Summary Cards */}
      <div className="agents-summary">
        <div className="summary-card">
          <Zap size={16} />
          <div>
            <span className="summary-value">{response.agents.length}</span>
            <span className="summary-label">Agents Used</span>
          </div>
        </div>
        <div className="summary-card">
          <Clock size={16} />
          <div>
            <span className="summary-value">
              {response.agents.reduce((sum, a) => sum + a.duration_ms, 0).toFixed(0)}ms
            </span>
            <span className="summary-label">Total Time</span>
          </div>
        </div>
        <div className="summary-card">
          <DollarSign size={16} />
          <div>
            <span className="summary-value">
              ${response.agents.reduce((sum, a) => sum + a.cost_usd, 0).toFixed(4)}
            </span>
            <span className="summary-label">Total Cost</span>
          </div>
        </div>
        <div className="summary-card">
          <Database size={16} />
          <div>
            <span className="summary-value">
              {response.agents.reduce((sum, a) => 
                sum + a.tools_invoked.filter(t => t.cache_hit).length, 0
              )}
            </span>
            <span className="summary-label">Cache Hits</span>
          </div>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="agents-list">
        {response.agents.map((agent, idx) => {
          const explanation = AGENT_EXPLANATIONS[agent.agent_name]
          const isExpanded = expandedAgent === agent.agent_id
          const cacheHits = agent.tools_invoked.filter(t => t.cache_hit).length
          const totalTools = agent.tools_invoked.length

          return (
            <div 
              key={agent.agent_id} 
              className={`agent-card ${isExpanded ? 'expanded' : ''} ${agent.error_message ? 'error' : 'success'}`}
            >
              <div 
                className="agent-card-header"
                onClick={() => toggleAgent(agent.agent_id)}
              >
                <div className="agent-info">
                  <div className="agent-index">{idx + 1}</div>
                  <div className="agent-details">
                    <h4 className="agent-name">{agent.agent_name}</h4>
                    {agent.model_used && (
                      <span className="agent-model">{agent.model_used}</span>
                    )}
                  </div>
                </div>
                
                <div className="agent-metrics">
                  <span className="metric">
                    <Clock size={12} />
                    {agent.duration_ms.toFixed(0)}ms
                  </span>
                  <span className="metric">
                    <DollarSign size={12} />
                    ${agent.cost_usd.toFixed(4)}
                  </span>
                  {cacheHits > 0 && (
                    <span className="metric cache-hit">
                      <Database size={12} />
                      {cacheHits}/{totalTools} cached
                    </span>
                  )}
                  <span className={`status-indicator ${agent.error_message ? 'error' : 'success'}`}>
                    {agent.error_message ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
                  </span>
                  <ChevronDown className={`expand-icon ${isExpanded ? 'rotated' : ''}`} size={16} />
                </div>
              </div>

              {isExpanded && (
                <div className="agent-card-body">
                  {/* Redis Benefits Explanation */}
                  {showExplanations && explanation && (
                    <div className="redis-explanation">
                      <div className="explanation-header">
                        <Database size={14} />
                        <span>Redis Integration Benefits</span>
                      </div>
                      <p className="explanation-role">{explanation.role}</p>
                      <p className="explanation-redis">{explanation.redisIntegration}</p>
                      <ul className="explanation-benefits">
                        {explanation.benefits.map((benefit, bidx) => (
                          <li key={bidx}>
                            <CheckCircle size={12} />
                            {benefit}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Token Usage */}
                  <div className="agent-section">
                    <h5>Token Usage</h5>
                    <div className="token-bars">
                      <div className="token-bar">
                        <span className="token-label">Input</span>
                        <div className="bar-container">
                          <div 
                            className="bar input" 
                            style={{ width: `${(agent.input_tokens / (agent.input_tokens + agent.output_tokens)) * 100}%` }}
                          />
                        </div>
                        <span className="token-value">{agent.input_tokens}</span>
                      </div>
                      <div className="token-bar">
                        <span className="token-label">Output</span>
                        <div className="bar-container">
                          <div 
                            className="bar output" 
                            style={{ width: `${(agent.output_tokens / (agent.input_tokens + agent.output_tokens)) * 100}%` }}
                          />
                        </div>
                        <span className="token-value">{agent.output_tokens}</span>
                      </div>
                    </div>
                  </div>

                  {/* Tools Invoked */}
                  {agent.tools_invoked.length > 0 && (
                    <div className="agent-section">
                      <h5>Tools Invoked ({agent.tools_invoked.length})</h5>
                      <div className="tools-list">
                        {agent.tools_invoked.map((tool, toolIdx) => (
                          <div key={toolIdx} className={`tool-item ${tool.cache_hit ? 'cached' : ''}`}>
                            <div className="tool-header">
                              <span className="tool-name">{tool.tool_name}</span>
                              {tool.cache_hit && (
                                <span className="cache-badge">
                                  <Database size={10} />
                                  CACHED
                                </span>
                              )}
                            </div>
                            <div className="tool-meta">
                              <span className="tool-duration">{tool.duration_ms.toFixed(0)}ms</span>
                              {tool.cache_similarity && (
                                <span className="tool-similarity">
                                  {(tool.cache_similarity * 100).toFixed(0)}% match
                                </span>
                              )}
                              <span className={`tool-status ${tool.status}`}>{tool.status}</span>
                            </div>
                            {showExplanations && tool.cache_hit && (
                              <div className="tool-benefit">
                                💡 This tool result was retrieved from Redis Tool Cache - 
                                saved an API call and {tool.duration_ms < 10 ? 'responded in milliseconds!' : 'reduced latency!'}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error Message */}
                  {agent.error_message && (
                    <div className="agent-error">
                      <AlertCircle size={14} />
                      {agent.error_message}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Overall Redis Benefits */}
      {showExplanations && (
        <div className="overall-benefits">
          <h4>🚀 How Redis Accelerated This Query</h4>
          <div className="benefits-grid">
            <div className="benefit-item">
              <span className="benefit-icon">🧠</span>
              <div>
                <strong>Semantic Cache</strong>
                <p>Similar queries return instantly without LLM calls</p>
              </div>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">🔧</span>
              <div>
                <strong>Tool Cache</strong>
                <p>{response.agents.reduce((sum, a) => 
                  sum + a.tools_invoked.filter(t => t.cache_hit).length, 0
                )} tool calls retrieved from cache</p>
              </div>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">🎯</span>
              <div>
                <strong>Semantic Routing</strong>
                <p>Query routed to workflow in &lt;5ms</p>
              </div>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">💾</span>
              <div>
                <strong>Contextual Memory</strong>
                <p>Your preferences remembered across sessions</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
