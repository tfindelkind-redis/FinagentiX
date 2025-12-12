import { Clock, Zap, Database, DollarSign } from 'lucide-react'
import type { EnhancedQueryResponse } from '@/types/api'
import './OverviewTab.css'

interface OverviewTabProps {
  response: EnhancedQueryResponse
}

export default function OverviewTab({ response }: OverviewTabProps) {
  const metrics = response.performance
  const costs = response.cost

  return (
    <div className="overview-tab">
      <div className="overview-grid">
        <div className="metric-card">
          <div className="metric-icon">
            <Clock size={20} />
          </div>
          <div className="metric-details">
            <div className="metric-label">Total Time</div>
            <div className="metric-value">{metrics.total_time_ms.toFixed(0)}ms</div>
            <div className="metric-sublabel">
              Processing: {metrics.processing_time_ms.toFixed(0)}ms • Queue: {metrics.queue_time_ms.toFixed(0)}ms
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon cost">
            <DollarSign size={20} />
          </div>
          <div className="metric-details">
            <div className="metric-label">Total Cost</div>
            <div className="metric-value">${costs.total_cost_usd.toFixed(4)}</div>
            <div className="metric-sublabel">
              {costs.cost_savings_percent > 0 ? '' : '+'}{(-costs.cost_savings_percent).toFixed(1)}% vs baseline
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon cache">
            <Database size={20} />
          </div>
          <div className="metric-details">
            <div className="metric-label">Cache Hit Rate</div>
            <div className="metric-value">{response.overall_cache_hit ? '100' : '0'}%</div>
            <div className="metric-sublabel">
              {response.cache_layers.filter(l => l.hit).length} hits • {response.cache_layers.filter(l => !l.hit && l.checked).length} misses
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon performance">
            <Zap size={20} />
          </div>
          <div className="metric-details">
            <div className="metric-label">Tokens</div>
            <div className="metric-value">{costs.llm_total_tokens.toLocaleString()}</div>
            <div className="metric-sublabel">
              {costs.llm_input_tokens.toLocaleString()} in • {costs.llm_output_tokens.toLocaleString()} out
            </div>
          </div>
        </div>
      </div>

      <div className="overview-section">
        <h3>Execution Summary</h3>
        <div className="summary-grid">
          <div className="summary-item">
            <span className="summary-label">Workflow Type:</span>
            <span className="summary-value">{response.workflow.workflow_name}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Agents Executed:</span>
            <span className="summary-value">{response.agents.length}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Tool Invocations:</span>
            <span className="summary-value">{response.agents.reduce((sum, a) => sum + a.tools_invoked.length, 0)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Cache Layers:</span>
            <span className="summary-value">{response.cache_layers.length}</span>
          </div>
        </div>
      </div>

      <div className="overview-section">
        <h3>Cost Breakdown</h3>
        <div className="cost-bars">
          {response.agents.map((agent) => (
            <div key={agent.agent_name} className="cost-bar-item">
              <div className="cost-bar-label">
                <span>{agent.agent_name}</span>
                <span className="cost-bar-value">${agent.cost_usd.toFixed(4)}</span>
              </div>
              <div className="cost-bar-track">
                <div
                  className="cost-bar-fill"
                  style={{ width: `${(agent.cost_usd / costs.total_cost_usd) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
