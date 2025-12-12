import { useState } from 'react'
import ChatPanel from './components/ChatPanel'
import MetricsPanel from './components/MetricsPanel'
import Header from './components/Header'
import type { EnhancedQueryResponse } from './types/api'

function App() {
  const [currentResponse, setCurrentResponse] = useState<EnhancedQueryResponse | null>(null)
  const [sessionId] = useState(() => `session_${Date.now()}`)

  return (
    <div className="app-container">
      <Header />
      <div className="main-content">
        <ChatPanel
          sessionId={sessionId}
          onResponseReceived={setCurrentResponse}
        />
        <MetricsPanel response={currentResponse} />
      </div>
    </div>
  )
}

export default App
