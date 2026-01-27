import { useState } from 'react'
import ChatPanel from './components/ChatPanel'
import MetricsPanel from './components/MetricsPanel'
import Header from './components/Header'
import RedisBenefits from './components/RedisBenefits'
import LoginModal from './components/auth/LoginModal'
import { useAuth } from './contexts/AuthContext'
import type { EnhancedQueryResponse } from './types/api'

type PageView = 'chat' | 'redis-benefits'

function App() {
  const { isAuthenticated, isLoading } = useAuth()
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

  // Show login modal if not authenticated
  if (!isAuthenticated && !isLoading) {
    return <LoginModal />
  }

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    )
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
