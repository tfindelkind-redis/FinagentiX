import { useState } from 'react'
import ChatPanel from './components/ChatPanel'
import MetricsPanel from './components/MetricsPanel'
import Header from './components/Header'
import RedisBenefits from './components/RedisBenefits'
import type { EnhancedQueryResponse } from './types/api'

type PageView = 'chat' | 'redis-benefits'

function App() {
  const [currentResponse, setCurrentResponse] = useState<EnhancedQueryResponse | null>(null)
  const [allResponses, setAllResponses] = useState<EnhancedQueryResponse[]>([])
  const [sessionId] = useState(() => `session_${Date.now()}`)
  const [currentPage, setCurrentPage] = useState<PageView>('chat')

  const handleResponseReceived = (response: EnhancedQueryResponse) => {
    setCurrentResponse(response)
    setAllResponses(prev => [...prev, response])
  }

  const handleClearSession = () => {
    setCurrentResponse(null)
    setAllResponses([])
  }

  return (
    <div className="app-container">
      <Header currentPage={currentPage} onPageChange={setCurrentPage} />
      {currentPage === 'chat' ? (
        <div className="main-content">
          <ChatPanel
            sessionId={sessionId}
            onResponseReceived={handleResponseReceived}
            onClearHistory={handleClearSession}
          />
          <MetricsPanel response={currentResponse} allResponses={allResponses} />
        </div>
      ) : (
        <div className="page-content">
          <RedisBenefits />
        </div>
      )}
    </div>
  )
}

export default App
