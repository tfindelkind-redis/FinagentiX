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
  explanation: string
  icon: React.ReactNode
  color: string
}> = {
  // === STEP 1: Query Processing & Embedding ===
  query_processing: {
    pattern: 'Query Processing',
    patternKey: 'semantic_cache',
    benefit: 'Starting the query pipeline - orchestrating all subsequent steps',
    explanation: 'This is the master orchestration step that coordinates the entire query flow. It manages the sequence: embed the question → check cache → route to agents → execute workflow → cache result. Think of it as the "conductor" of the AI orchestra.',
    icon: <Clock size={14} />,
    color: 'var(--color-text-primary)'
  },
  embedding_generation: {
    pattern: 'Query Embedding',
    patternKey: 'semantic_cache',
    benefit: 'Converting your question into a vector for semantic matching',
    explanation: 'The user\'s question is converted into a numerical vector (embedding) using Azure OpenAI. This vector captures the "meaning" of the question, enabling semantic similarity search. The same question worded differently will have similar vectors, which is how we find cached answers for paraphrased questions.',
    icon: <Brain size={14} />,
    color: 'var(--color-info)'
  },

  // === STEP 2: Cache Operations ===
  cache_check: {
    pattern: 'Semantic Cache Lookup',
    patternKey: 'semantic_cache',
    benefit: 'Searching Redis for semantically similar questions already answered',
    explanation: 'Redis Vector Search compares the query embedding against previously cached question-answer pairs. If a similar question (>85% similarity) exists, we return that answer instantly. This typically saves $0.01-0.03 and 2-3 seconds per cache hit.',
    icon: <Database size={14} />,
    color: 'var(--color-success)'
  },
  cache_hit: {
    pattern: 'Semantic Cache HIT',
    patternKey: 'semantic_cache',
    benefit: '🎉 Found a cached answer! Skipping LLM call entirely',
    explanation: 'Success! A semantically similar question was found. The cached answer is returned immediately without calling the LLM. This is where Redis delivers massive value: instant responses at near-zero cost. The hit rate improves over time as more queries are cached.',
    icon: <Zap size={14} />,
    color: 'var(--color-warning)'
  },
  cache_miss: {
    pattern: 'Semantic Cache MISS',
    patternKey: 'semantic_cache',
    benefit: 'No similar question found - proceeding to generate fresh answer',
    explanation: 'No matching question found in the cache (similarity below threshold). The query will be processed normally by the AI agents, and the result will be cached for future similar questions. This is expected for novel questions.',
    icon: <Database size={14} />,
    color: 'var(--color-text-muted)'
  },
  cache_set: {
    pattern: 'Cache Storage',
    patternKey: 'semantic_cache',
    benefit: 'Storing the answer for future similar questions',
    explanation: 'The question-answer pair is being stored in Redis with its embedding vector. Future questions with similar meaning will match against this entry. Entries have a TTL (time-to-live) to ensure data freshness for time-sensitive information.',
    icon: <Database size={14} />,
    color: 'var(--color-success)'
  },

  // === STEP 3: Context & Routing ===
  context_loading: {
    pattern: 'User Context',
    patternKey: 'contextual_memory',
    benefit: 'Loading conversation history and user preferences from Redis',
    explanation: 'Redis retrieves the user\'s session data: conversation history, preferences, portfolio holdings, and previous interactions. This context enables personalized responses ("Based on your interest in tech stocks...") without asking the user to repeat information.',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  },
  routing: {
    pattern: 'Semantic Router',
    patternKey: 'semantic_routing',
    benefit: 'Determining which specialized agent should handle this query',
    explanation: 'Instead of asking every agent (slow and expensive), Redis Vector Search matches the query intent against predefined route patterns. For example, "What\'s AAPL trading at?" routes to the Market Data agent, while "Explain P/E ratio" routes to the Research agent. This is like an intelligent switchboard.',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  },

  // === STEP 4: RAG & Document Retrieval ===
  rag_retrieval: {
    pattern: 'Document Context (RAG)',
    patternKey: 'document_store',
    benefit: 'Finding relevant SEC filings and documents to ground the response',
    explanation: 'Retrieval-Augmented Generation: Redis performs vector similarity search across our document corpus (SEC filings, earnings reports, news). The most relevant passages are retrieved in milliseconds and provided to the LLM as context, ensuring responses are grounded in real data rather than hallucinated.',
    icon: <Database size={14} />,
    color: 'var(--color-info)'
  },
  rag_query: {
    pattern: 'Document Search',
    patternKey: 'document_store',
    benefit: 'Vector similarity search finding relevant document passages',
    explanation: 'A specific RAG query is being executed. Redis searches through indexed documents using vector similarity, returning the top-K most relevant passages. These passages become part of the LLM prompt, dramatically improving answer accuracy for factual questions.',
    icon: <Database size={14} />,
    color: 'var(--color-info)'
  },

  // === STEP 5: Agent Execution ===
  agent_start: {
    pattern: 'Agent Starting',
    patternKey: 'contextual_memory',
    benefit: 'Specialized AI agent beginning work on your query',
    explanation: 'A specialized agent is starting to process the query. Each agent has domain expertise (market data, portfolio analysis, research) and access to specific tools. The agent uses cached tool results and conversation memory from Redis to work efficiently.',
    icon: <Brain size={14} />,
    color: 'var(--color-info)'
  },
  agent_end: {
    pattern: 'Agent Complete',
    patternKey: 'workflow_persistence',
    benefit: 'Agent finished - results saved for recovery and audit',
    explanation: 'The agent has completed its task. Results and workflow state are persisted to Redis, enabling: (1) recovery if a later step fails, (2) audit trail for compliance, and (3) debugging visibility. This ensures reliability in production environments.',
    icon: <CheckCircle size={14} />,
    color: 'var(--color-success)'
  },

  // === STEP 6: Workflow Execution ===
  workflow_execution: {
    pattern: 'Workflow Running',
    patternKey: 'workflow_persistence',
    benefit: 'Coordinating multiple agents to answer your question',
    explanation: 'A multi-agent workflow is executing. This may involve sequential agents (one after another) or parallel execution. Redis maintains workflow state, enabling checkpointing and recovery. Complex questions may trigger multiple specialized agents working together.',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  },
  workflow_checkpoint: {
    pattern: 'Workflow Checkpoint',
    patternKey: 'workflow_persistence',
    benefit: 'Saving progress - can resume from here if something fails',
    explanation: 'A checkpoint is saved to Redis capturing current workflow state. If the system crashes or an error occurs later, processing resumes from this checkpoint rather than restarting. Critical for long-running operations and enterprise reliability requirements.',
    icon: <Shield size={14} />,
    color: 'var(--color-success)'
  },

  // === Tool & Memory Operations ===
  tool_call: {
    pattern: 'Tool Execution',
    patternKey: 'tool_cache',
    benefit: 'Calling external API - result will be cached with TTL',
    explanation: 'The agent is calling an external service (stock quotes, news API, financial data). Results are cached in Redis with appropriate TTL. For example, stock prices might cache for 1 minute, while company profiles cache for 24 hours. This reduces API costs and latency for repeated requests.',
    icon: <Zap size={14} />,
    color: 'var(--color-accent)'
  },
  memory_lookup: {
    pattern: 'Memory Retrieval',
    patternKey: 'contextual_memory',
    benefit: 'Retrieving relevant memories for personalized response',
    explanation: 'Redis retrieves relevant conversation memories using vector similarity. The system finds past interactions related to the current query ("You asked about AAPL last week"). This enables coherent, contextual conversations across sessions.',
    icon: <Brain size={14} />,
    color: 'var(--color-primary)'
  }
}

// Fallback for unknown event types
const DEFAULT_EVENT_INFO = {
  pattern: 'Processing Step',
  patternKey: 'semantic_cache' as const,
  benefit: 'Processing step in the AI workflow',
  explanation: 'A processing step in the query pipeline. The system is performing operations that may involve Redis for caching, state management, or vector operations. Each step contributes to generating an accurate, fast response.',
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

  // Calculate savings summary - count both cache_hit type AND cache_check with status='hit'
  const cacheHits = timeline.events.filter(e => 
    e.type === 'cache_hit' || (e.type === 'cache_check' && e.status === 'hit')
  ).length
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
                  {/* Status Badge - Shows HIT/MISS/SUCCESS prominently */}
                  {event.status && (
                    <span className={`event-status-badge status-${event.status}`}>
                      {event.status === 'hit' ? '✓ HIT' : 
                       event.status === 'miss' ? '✗ MISS' : 
                       event.status === 'success' ? '✓' : event.status.toUpperCase()}
                    </span>
                  )}
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

                {/* PO-Friendly Explanation */}
                {showExplanations && (
                  <div className="po-explanation">
                    <p>{eventInfo.explanation}</p>
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
