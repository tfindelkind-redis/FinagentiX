import { useState } from 'react'
import { Clock, Zap, Database, Brain, Shield, CheckCircle, Info, ChevronDown, ChevronRight } from 'lucide-react'
import type { EnhancedQueryResponse } from '@/types/api'
import { REDIS_PATTERN_EXPLANATIONS } from '@/data/learnModeQuestions'
import './TimelineTab.css'
import './TimelineTabEnhanced.css'

interface TimelineTabEnhancedProps {
  response: EnhancedQueryResponse
}

// Map event types to Redis patterns and their benefits
const EVENT_REDIS_MAPPING: Record<string, {
  pattern: string
  patternKey: keyof typeof REDIS_PATTERN_EXPLANATIONS
  benefit: string
  icon: React.ReactNode
  color: string
}> = {
  cache_check: {
    pattern: 'Semantic Cache',
    patternKey: 'semantic_cache',
    benefit: 'Checking if a semantically similar query was answered before - saves LLM costs and latency',
    icon: <Database size={14} />,
    color: 'var(--color-success)'
  },
  cache_hit: {
    pattern: 'Semantic Cache HIT',
    patternKey: 'semantic_cache',
    benefit: '🎉 Found cached response! Saved ~$0.01 and ~2 seconds by reusing previous answer',
    icon: <Zap size={14} />,
    color: 'var(--color-warning)'
  },
  cache_miss: {
    pattern: 'Semantic Cache MISS',
    patternKey: 'semantic_cache',
    benefit: 'No similar query found - will process and cache this for future requests',
    icon: <Database size={14} />,
    color: 'var(--color-text-muted)'
  },
  routing: {
    pattern: 'Semantic Router',
    patternKey: 'semantic_routing',
    benefit: 'AI analyzes query intent to route to the best agent - faster than asking every agent',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  },
  agent_start: {
    pattern: 'Agent Execution',
    patternKey: 'contextual_memory',
    benefit: 'Agent starting work - may use cached tool results and contextual memory',
    icon: <Brain size={14} />,
    color: 'var(--color-info)'
  },
  agent_end: {
    pattern: 'Agent Complete',
    patternKey: 'workflow_persistence',
    benefit: 'Agent finished - results persisted for recovery and future reference',
    icon: <CheckCircle size={14} />,
    color: 'var(--color-success)'
  },
  tool_call: {
    pattern: 'Tool Cache',
    patternKey: 'tool_cache',
    benefit: 'Calling external API/tool - results will be cached with TTL for repeated calls',
    icon: <Zap size={14} />,
    color: 'var(--color-accent)'
  },
  rag_query: {
    pattern: 'Document Store (RAG)',
    patternKey: 'document_store',
    benefit: 'Vector similarity search across SEC filings and news - finds relevant context instantly',
    icon: <Database size={14} />,
    color: 'var(--color-info)'
  },
  memory_lookup: {
    pattern: 'Contextual Memory',
    patternKey: 'contextual_memory',
    benefit: 'Retrieving conversation history and user preferences for personalized response',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  },
  workflow_checkpoint: {
    pattern: 'Workflow Persistence',
    patternKey: 'workflow_persistence',
    benefit: 'Saving checkpoint - if process fails, can resume from here instead of starting over',
    icon: <Shield size={14} />,
    color: 'var(--color-success)'
  }
}

// Fallback for unknown event types
const DEFAULT_EVENT_INFO = {
  pattern: 'Processing',
  patternKey: 'semantic_cache' as const,
  benefit: 'Processing step in the workflow',
  icon: <Clock size={14} />,
  color: 'var(--color-text-muted)'
}

export default function TimelineTabEnhanced({ response }: TimelineTabEnhancedProps) {
  const timeline = response.timeline
  const [showExplanations, setShowExplanations] = useState(true)
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set())

  const toggleEvent = (idx: number) => {
    setExpandedEvents(prev => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  // Calculate savings summary
  const cacheHits = timeline.events.filter(e => e.type === 'cache_hit').length
  const totalEvents = timeline.events.length
  const estimatedSavings = cacheHits * 0.01 // $0.01 per cache hit
  const estimatedTimeSaved = cacheHits * 2000 // 2 seconds per cache hit

  return (
    <div className="timeline-tab timeline-tab-enhanced">
      <div className="timeline-header-row">
        <h3>Execution Timeline</h3>
        <label className="show-explanations-toggle">
          <input
            type="checkbox"
            checked={showExplanations}
            onChange={(e) => setShowExplanations(e.target.checked)}
          />
          <Info size={14} />
          <span>Show Redis Insights</span>
        </label>
      </div>

      {/* Summary Cards */}
      <div className="timeline-summary">
        <div className="summary-card">
          <div className="summary-icon"><Clock size={16} /></div>
          <div className="summary-content">
            <span className="summary-value">{totalEvents}</span>
            <span className="summary-label">Steps</span>
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-icon"><Zap size={16} /></div>
          <div className="summary-content">
            <span className="summary-value">{cacheHits}</span>
            <span className="summary-label">Cache Hits</span>
          </div>
        </div>
        <div className="summary-card highlight">
          <div className="summary-icon"><Database size={16} /></div>
          <div className="summary-content">
            <span className="summary-value">${estimatedSavings.toFixed(2)}</span>
            <span className="summary-label">Est. Saved</span>
          </div>
        </div>
        <div className="summary-card highlight">
          <div className="summary-icon"><Clock size={16} /></div>
          <div className="summary-content">
            <span className="summary-value">{(estimatedTimeSaved / 1000).toFixed(1)}s</span>
            <span className="summary-label">Time Saved</span>
          </div>
        </div>
      </div>

      <div className="timeline-container">
        {timeline.events.map((event, idx) => {
          const eventInfo = EVENT_REDIS_MAPPING[event.type] || DEFAULT_EVENT_INFO
          const isExpanded = expandedEvents.has(idx)
          const patternDetails = REDIS_PATTERN_EXPLANATIONS[eventInfo.patternKey]

          return (
            <div key={idx} className="timeline-event enhanced">
              <div className="timeline-marker">
                <div 
                  className={`timeline-dot ${event.type}`} 
                  style={{ borderColor: eventInfo.color }}
                >
                  {eventInfo.icon}
                </div>
                {idx < timeline.events.length - 1 && <div className="timeline-line" />}
              </div>
              <div className="timeline-content">
                <div className="timeline-header">
                  <span 
                    className={`event-type ${event.type}`}
                    style={{ color: eventInfo.color }}
                  >
                    {event.type.replace(/_/g, ' ')}
                  </span>
                  <span className="event-time">
                    {event.start_time_ms.toFixed(0)}ms
                  </span>
                </div>

                {event.name && (
                  <div className="event-agent">{event.name}</div>
                )}

                {/* Redis Pattern Badge */}
                {showExplanations && (
                  <div className="redis-pattern-badge" style={{ borderColor: eventInfo.color }}>
                    <span className="pattern-name">{eventInfo.pattern}</span>
                  </div>
                )}

                {/* Benefit Explanation */}
                {showExplanations && (
                  <div className="benefit-explanation">
                    <Info size={12} />
                    <span>{eventInfo.benefit}</span>
                  </div>
                )}

                {/* Expandable Details */}
                <button 
                  className="expand-details-btn"
                  onClick={() => toggleEvent(idx)}
                >
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span>{isExpanded ? 'Hide Details' : 'Show Details'}</span>
                </button>

                {isExpanded && (
                  <div className="expanded-details">
                    {/* Redis Pattern Deep Dive */}
                    {showExplanations && patternDetails && (
                      <div className="pattern-deep-dive">
                        <h5>{patternDetails.icon} {patternDetails.name}</h5>
                        <p className="pattern-description">{patternDetails.description}</p>
                        <div className="how-it-works">
                          <strong>How it works:</strong>
                          <p>{patternDetails.howItWorks}</p>
                        </div>
                        <div className="pattern-benefit">
                          <strong>Benefit:</strong>
                          <p>{patternDetails.benefit}</p>
                        </div>
                      </div>
                    )}

                    {/* Event Metadata */}
                    {event.metadata && Object.keys(event.metadata).length > 0 && (
                      <details className="event-metadata" open>
                        <summary>Event Metadata</summary>
                        <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                      </details>
                    )}
                  </div>
                )}

                {event.duration_ms !== undefined && (
                  <div className="event-duration">
                    <Clock size={12} />
                    <span>Duration: {event.duration_ms.toFixed(0)}ms</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Redis Benefits Summary */}
      {showExplanations && (
        <div className="redis-timeline-summary">
          <h4>🚀 How Redis Optimized This Query</h4>
          <div className="optimization-grid">
            <div className="optimization-item">
              <strong>Semantic Caching</strong>
              <p>Similar queries return instantly without re-calling LLM</p>
            </div>
            <div className="optimization-item">
              <strong>Vector Search</strong>
              <p>Sub-millisecond similarity search across documents</p>
            </div>
            <div className="optimization-item">
              <strong>Tool Result Caching</strong>
              <p>API responses cached with TTL to reduce external calls</p>
            </div>
            <div className="optimization-item">
              <strong>Workflow State</strong>
              <p>Progress saved for recovery and debugging</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
