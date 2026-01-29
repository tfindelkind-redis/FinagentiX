import { Activity, MessageSquare, Zap, AlertTriangle, LogOut, User, Info } from 'lucide-react'
import { useState, useEffect } from 'react'
import CacheControls from './CacheControls'
import { useAuth } from '../contexts/AuthContext'
import { getApiVersion, getFrontendVersion, type BuildInfo } from '../lib/api'
import './Header.css'

type PageView = 'chat' | 'redis-benefits'

interface HeaderProps {
  currentPage: PageView
  onPageChange: (page: PageView) => void
}

export default function Header({ currentPage, onPageChange }: HeaderProps) {
  const { username, logout } = useAuth()
  const [showVersionInfo, setShowVersionInfo] = useState(false)
  const [apiVersion, setApiVersion] = useState<BuildInfo | null>(null)
  const frontendVersion = getFrontendVersion()

  useEffect(() => {
    // Fetch API version when version popup is shown
    if (showVersionInfo && !apiVersion) {
      getApiVersion()
        .then(setApiVersion)
        .catch((err) => console.error('Failed to fetch API version:', err))
    }
  }, [showVersionInfo, apiVersion])

  const shortCommit = (commit: string) => commit.slice(0, 7)

  return (
    <>
      <div className="demo-disclaimer">
        <AlertTriangle size={14} />
        <span>Demo Only – Uses historical data. Not financial advice.</span>
      </div>
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <div className="header-title">
              <Activity size={28} className="header-icon" />
              <h1>FinagentiX</h1>
              <span className="header-subtitle">Agent-based AI Financial Assistant</span>
            </div>
            <div className="status-indicator">
              <span className="status-dot status-online"></span>
              <span className="status-text">Online</span>
            </div>
          </div>
          <nav className="header-nav">
            <button 
              className={`nav-tab ${currentPage === 'chat' ? 'nav-tab-active' : ''}`}
              onClick={() => onPageChange('chat')}
            >
              <MessageSquare size={18} />
              Chat
            </button>
            <button 
              className={`nav-tab ${currentPage === 'redis-benefits' ? 'nav-tab-active' : ''}`}
              onClick={() => onPageChange('redis-benefits')}
            >
              <Zap size={18} />
              Redis Benefits
            </button>
          </nav>
          <div className="header-right">
            <CacheControls />
            <div className="version-info-container">
              <button 
                className="version-button" 
                onClick={() => setShowVersionInfo(!showVersionInfo)}
                title="Version info"
              >
                <Info size={16} />
              </button>
              {showVersionInfo && (
                <div className="version-popup">
                  <div className="version-section">
                    <h4>Frontend</h4>
                    <div className="version-row">
                      <span>Commit:</span>
                      <code>{shortCommit(frontendVersion.git_commit)}</code>
                    </div>
                    <div className="version-row">
                      <span>Branch:</span>
                      <code>{frontendVersion.git_branch}</code>
                    </div>
                    <div className="version-row">
                      <span>Built:</span>
                      <code>{frontendVersion.build_time}</code>
                    </div>
                  </div>
                  <div className="version-section">
                    <h4>API</h4>
                    {apiVersion ? (
                      <>
                        <div className="version-row">
                          <span>Commit:</span>
                          <code>{shortCommit(apiVersion.git_commit)}</code>
                        </div>
                        <div className="version-row">
                          <span>Branch:</span>
                          <code>{apiVersion.git_branch}</code>
                        </div>
                        <div className="version-row">
                          <span>Built:</span>
                          <code>{apiVersion.build_time}</code>
                        </div>
                      </>
                    ) : (
                      <div className="version-row">Loading...</div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="user-menu">
              <span className="user-name">
                <User size={16} />
                {username}
              </span>
              <button className="logout-button" onClick={logout} title="Sign out">
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </header>
    </>
  )
}
