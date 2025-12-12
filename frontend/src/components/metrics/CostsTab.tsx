import { TrendingUp, TrendingDown } from 'lucide-react'
import type { EnhancedQueryResponse } from '@/types/api'
import './CostsTab.css'

interface CostsTabProps {
  response: EnhancedQueryResponse
}

export default function CostsTab({ response }: CostsTabProps) {
  const costs = response.cost
  const isAboveBaseline = costs.cost_savings_percent < 0

  return (
    <div className="costs-tab">
      <div className="cost-summary">
        <div className="cost-header">
          <h3>Cost Breakdown</h3>
          <div className="cost-total">${costs.total_cost_usd.toFixed(4)}</div>
        </div>
        
        <div className="baseline-comparison">
          <div className="comparison-label">vs Baseline</div>
          <div className={`comparison-value ${isAboveBaseline ? 'above' : 'below'}`}>
            {isAboveBaseline ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {isAboveBaseline ? '+' : ''}{(-costs.cost_savings_percent).toFixed(1)}%
            <span className="comparison-amount">
              (${Math.abs(costs.cost_savings_usd).toFixed(4)})
            </span>
          </div>
        </div>
      </div>

      <div className="cost-details">
        <div className="cost-row">
          <span>LLM Input Tokens:</span>
          <span>{costs.llm_input_tokens.toLocaleString()}</span>
          <strong>${(costs.llm_cost_usd * costs.llm_input_tokens / costs.llm_total_tokens).toFixed(4)}</strong>
        </div>
        <div className="cost-row">
          <span>LLM Output Tokens:</span>
          <span>{costs.llm_output_tokens.toLocaleString()}</span>
          <strong>${(costs.llm_cost_usd * costs.llm_output_tokens / costs.llm_total_tokens).toFixed(4)}</strong>
        </div>
        <div className="cost-row">
          <span>Embeddings:</span>
          <span>{costs.embedding_total_tokens.toLocaleString()} tokens</span>
          <strong>${costs.embedding_cost_usd.toFixed(4)}</strong>
        </div>
      </div>

      <div className="agent-costs">
        <h4>Cost by Agent</h4>
        <div className="agent-cost-list">
          {response.agents.map((agent, idx) => (
            <div key={idx} className="agent-cost-item">
              <div className="agent-cost-header">
                <span className="agent-cost-name">{agent.agent_name}</span>
                <span className="agent-cost-value">${agent.cost_usd.toFixed(4)}</span>
              </div>
              <div className="agent-cost-tokens">
                {agent.input_tokens.toLocaleString()} in · {agent.output_tokens.toLocaleString()} out
              </div>
              <div className="agent-cost-bar">
                <div
                  className="agent-cost-fill"
                  style={{ width: `${(agent.cost_usd / costs.total_cost_usd) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="savings-estimate">
        <h4>Cost Savings</h4>
        <div className="savings-grid">
          <div className="savings-item">
            <span className="savings-label">Baseline Cost:</span>
            <span className="savings-value">
              ${costs.baseline_cost_usd.toFixed(4)}
            </span>
          </div>
          <div className="savings-item">
            <span className="savings-label">Actual Cost:</span>
            <span className="savings-value">
              ${costs.total_cost_usd.toFixed(4)}
            </span>
          </div>
          <div className="savings-item">
            <span className="savings-label">Total Savings:</span>
            <span className="savings-value success">
              ${costs.cost_savings_usd.toFixed(4)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
