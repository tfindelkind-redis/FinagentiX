import { useState } from 'react'
import { BarChart3, Clock, DollarSign, Network } from 'lucide-react'
import type { EnhancedQueryResponse } from '@/types/api'
import OverviewTab from './metrics/OverviewTab'
import AgentsTab from './metrics/AgentsTab'
import TimelineTab from './metrics/TimelineTab'
import CostsTab from './metrics/CostsTab'
import './MetricsPanel.css'

interface MetricsPanelProps {
  response: EnhancedQueryResponse | null
}

type Tab = 'overview' | 'agents' | 'timeline' | 'costs'

export default function MetricsPanel({ response }: MetricsPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  if (!response) {
    return (
      <div className="metrics-panel">
        <div className="metrics-empty">
          <BarChart3 size={48} />
          <h3>No Metrics Yet</h3>
          <p>Submit a query to see detailed execution metrics.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="metrics-panel">
      <div className="metrics-header">
        <h2>Metrics</h2>
        <span className="query-id">ID: {response.query_id.slice(0, 8)}</span>
      </div>

      <div className="metrics-tabs">
        <button
          className={`metrics-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <BarChart3 size={16} />
          Overview
        </button>
        <button
          className={`metrics-tab ${activeTab === 'agents' ? 'active' : ''}`}
          onClick={() => setActiveTab('agents')}
        >
          <Network size={16} />
          Agents
        </button>
        <button
          className={`metrics-tab ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
        >
          <Clock size={16} />
          Timeline
        </button>
        <button
          className={`metrics-tab ${activeTab === 'costs' ? 'active' : ''}`}
          onClick={() => setActiveTab('costs')}
        >
          <DollarSign size={16} />
          Costs
        </button>
      </div>

      <div className="metrics-content">
        {activeTab === 'overview' && <OverviewTab response={response} />}
        {activeTab === 'agents' && <AgentsTab response={response} />}
        {activeTab === 'timeline' && <TimelineTab response={response} />}
        {activeTab === 'costs' && <CostsTab response={response} />}
      </div>
    </div>
  )
}
