import { TrendingUp, TrendingDown, Calculator, History } from 'lucide-react'
import type { EnhancedQueryResponse } from '@/types/api'
import pricingData from '@/data/pricing.json'
import './CostsTab.css'

interface CostsTabProps {
  response: EnhancedQueryResponse
  allResponses?: EnhancedQueryResponse[]
}

// Get GPT-4o pricing from our local pricing data
const gpt4oPricing = pricingData.models['gpt-4o'].pricing.payAsYouGo
const embeddingPricing = pricingData.embeddings['text-embedding-3-large'].pricing

// Calculate cost from tokens using local pricing
function calculateLLMCost(inputTokens: number, outputTokens: number, cachedInputTokens: number = 0) {
  const inputCost = ((inputTokens - cachedInputTokens) / 1_000_000) * gpt4oPricing.inputPer1MTokens
  const cachedCost = (cachedInputTokens / 1_000_000) * gpt4oPricing.cachedInputPer1MTokens
  const outputCost = (outputTokens / 1_000_000) * gpt4oPricing.outputPer1MTokens
  return { inputCost, cachedCost, outputCost, total: inputCost + cachedCost + outputCost }
}

function calculateEmbeddingCost(tokens: number) {
  return (tokens / 1_000_000) * embeddingPricing.per1MTokens
}

// Calculate aggregated session costs
function calculateSessionCosts(responses: EnhancedQueryResponse[]) {
  let totalInputTokens = 0
  let totalOutputTokens = 0
  let totalEmbeddingTokens = 0
  let cacheHits = 0
  
  responses.forEach(r => {
    totalInputTokens += r.cost.llm_input_tokens
    totalOutputTokens += r.cost.llm_output_tokens
    totalEmbeddingTokens += r.cost.embedding_total_tokens
    // Count cache hits from timeline events
    const hits = r.timeline.events.filter(e => 
      e.type === 'cache_hit' || (e.type === 'cache_check' && e.status === 'hit')
    ).length
    cacheHits += hits
  })
  
  const llmCost = calculateLLMCost(totalInputTokens, totalOutputTokens)
  const embeddingCost = calculateEmbeddingCost(totalEmbeddingTokens)
  const totalCost = llmCost.total + embeddingCost
  
  // Baseline assumes no caching
  const baselineLLM = calculateLLMCost(totalInputTokens, totalOutputTokens, 0)
  const baselineCost = baselineLLM.total + embeddingCost
  
  return {
    totalInputTokens,
    totalOutputTokens,
    totalEmbeddingTokens,
    totalCost,
    baselineCost,
    savings: baselineCost - totalCost,
    cacheHits,
    queryCount: responses.length
  }
}

export default function CostsTab({ response, allResponses = [] }: CostsTabProps) {
  const costs = response.cost
  
  // Calculate costs for current request using local GPT-4o pricing
  const calculatedLLM = calculateLLMCost(costs.llm_input_tokens, costs.llm_output_tokens)
  const calculatedEmbedding = calculateEmbeddingCost(costs.embedding_total_tokens)
  const calculatedTotal = calculatedLLM.total + calculatedEmbedding
  
  // Calculate baseline (no caching - all input tokens at full price)
  const baselineLLM = calculateLLMCost(costs.llm_input_tokens, costs.llm_output_tokens, 0)
  const calculatedBaseline = baselineLLM.total + calculatedEmbedding
  
  const calculatedSavings = calculatedBaseline - calculatedTotal
  const calculatedSavingsPercent = calculatedBaseline > 0 
    ? (calculatedSavings / calculatedBaseline) * 100 
    : 0
  
  const isAboveBaseline = calculatedSavingsPercent < 0
  
  // Calculate session aggregates
  const session = calculateSessionCosts(allResponses)
  const sessionSavingsPercent = session.baselineCost > 0 
    ? (session.savings / session.baselineCost) * 100 
    : 0

  return (
    <div className="costs-tab">
      {/* Session Summary - Aggregated View */}
      {allResponses.length > 0 && (
        <div className="session-summary">
          <div className="session-header">
            <History size={16} />
            <h3>Session Summary</h3>
            <span className="session-query-count">{session.queryCount} queries</span>
          </div>
          
          <div className="session-stats">
            <div className="session-stat">
              <span className="stat-label">Total Cost</span>
              <span className="stat-value">${session.totalCost.toFixed(4)}</span>
            </div>
            <div className="session-stat">
              <span className="stat-label">Baseline Cost</span>
              <span className="stat-value muted">${session.baselineCost.toFixed(4)}</span>
            </div>
            <div className="session-stat highlight">
              <span className="stat-label">Total Saved</span>
              <span className="stat-value success">${session.savings.toFixed(4)}</span>
            </div>
            <div className="session-stat highlight">
              <span className="stat-label">Savings %</span>
              <span className="stat-value success">{sessionSavingsPercent.toFixed(1)}%</span>
            </div>
          </div>
          
          <div className="session-tokens">
            <span>{session.totalInputTokens.toLocaleString()} input</span>
            <span>·</span>
            <span>{session.totalOutputTokens.toLocaleString()} output</span>
            <span>·</span>
            <span>{session.cacheHits} cache hits</span>
          </div>
        </div>
      )}

      {/* Current Request Costs */}
      <div className="cost-summary">
        <div className="cost-header">
          <h3>Current Request</h3>
          <div className="cost-model-badge">
            <Calculator size={14} />
            GPT-4o Pricing
          </div>
          <div className="cost-total">${calculatedTotal.toFixed(4)}</div>
        </div>
        
        <div className="baseline-comparison">
          <div className="comparison-label">vs Baseline (no cache)</div>
          <div className={`comparison-value ${isAboveBaseline ? 'above' : 'below'}`}>
            {isAboveBaseline ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {isAboveBaseline ? '+' : '-'}{Math.abs(calculatedSavingsPercent).toFixed(1)}%
            <span className="comparison-amount">
              (${Math.abs(calculatedSavings).toFixed(4)})
            </span>
          </div>
        </div>
      </div>

      <div className="cost-details">
        <div className="cost-row">
          <span>LLM Input Tokens:</span>
          <span>{costs.llm_input_tokens.toLocaleString()}</span>
          <strong>${calculatedLLM.inputCost.toFixed(4)}</strong>
        </div>
        <div className="cost-row">
          <span>LLM Output Tokens:</span>
          <span>{costs.llm_output_tokens.toLocaleString()}</span>
          <strong>${calculatedLLM.outputCost.toFixed(4)}</strong>
        </div>
        <div className="cost-row">
          <span>Embeddings:</span>
          <span>{costs.embedding_total_tokens.toLocaleString()} tokens</span>
          <strong>${calculatedEmbedding.toFixed(4)}</strong>
        </div>
      </div>
      
      <div className="pricing-info">
        <div className="pricing-rates">
          <span className="rate">Input: ${gpt4oPricing.inputPer1MTokens}/1M</span>
          <span className="rate">Output: ${gpt4oPricing.outputPer1MTokens}/1M</span>
          <span className="rate">Cached: ${gpt4oPricing.cachedInputPer1MTokens}/1M</span>
        </div>
      </div>

      <div className="agent-costs">
        <h4>Cost by Agent</h4>
        <div className="agent-cost-list">
          {response.agents.map((agent, idx) => {
            // Calculate agent cost using local pricing
            const agentLLMCost = calculateLLMCost(agent.input_tokens, agent.output_tokens)
            return (
              <div key={idx} className="agent-cost-item">
                <div className="agent-cost-header">
                  <span className="agent-cost-name">{agent.agent_name}</span>
                  <span className="agent-cost-value">${agentLLMCost.total.toFixed(4)}</span>
                </div>
                <div className="agent-cost-tokens">
                  {agent.input_tokens.toLocaleString()} in · {agent.output_tokens.toLocaleString()} out
                </div>
                <div className="agent-cost-bar">
                  <div
                    className="agent-cost-fill"
                    style={{ width: `${(agentLLMCost.total / calculatedTotal) * 100}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="savings-estimate">
        <h4>Request Savings</h4>
        <div className="savings-grid">
          <div className="savings-item">
            <span className="savings-label">Baseline Cost:</span>
            <span className="savings-value">
              ${calculatedBaseline.toFixed(4)}
            </span>
          </div>
          <div className="savings-item">
            <span className="savings-label">Actual Cost:</span>
            <span className="savings-value">
              ${calculatedTotal.toFixed(4)}
            </span>
          </div>
          <div className="savings-item">
            <span className="savings-label">Savings:</span>
            <span className="savings-value success">
              ${calculatedSavings.toFixed(4)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
