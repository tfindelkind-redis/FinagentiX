import type { EnhancedQueryResponse } from '@/types/api'
import './AgentsTab.css'

interface AgentsTabProps {
  response: EnhancedQueryResponse
}

export default function AgentsTab({ response }: AgentsTabProps) {
  return (
    <div className="agents-tab">
      <h3>Agent Execution Details</h3>
      <div className="agents-table">
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Duration</th>
              <th>Tokens</th>
              <th>Cost</th>
              <th>Tools</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {response.agents.map((agent, idx) => (
              <tr key={idx}>
                <td>
                  <div className="agent-name">{agent.agent_name}</div>
                  {agent.model_used && <div className="agent-model">{agent.model_used}</div>}
                </td>
                <td>{agent.duration_ms.toFixed(0)}ms</td>
                <td>
                  {agent.input_tokens + agent.output_tokens}
                  <span className="token-detail">
                    ({agent.input_tokens}/{agent.output_tokens})
                  </span>
                </td>
                <td>${agent.cost_usd.toFixed(4)}</td>
                <td>
                  {agent.tools_invoked.length > 0 ? (
                    <details>
                      <summary>{agent.tools_invoked.length} tools</summary>
                      <ul className="tool-list">
                        {agent.tools_invoked.map((tool, toolIdx) => (
                          <li key={toolIdx}>
                            <strong>{tool.tool_name}</strong>
                            {tool.cache_hit && <span className="cache-badge">Cached</span>}
                            <div className="tool-time">{tool.duration_ms.toFixed(0)}ms</div>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <span className="text-muted">None</span>
                  )}
                </td>
                <td>
                  <span className={`status-badge ${agent.error_message ? 'error' : 'success'}`}>
                    {agent.error_message ? 'Error' : 'Success'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
