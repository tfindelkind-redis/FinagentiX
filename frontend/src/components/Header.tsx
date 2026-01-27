import { Activity, MessageSquare, Zap, AlertTriangle, LogOut, User } from 'lucide-react'
import CacheControls from './CacheControls'
import { useAuth } from '../contexts/AuthContext'
import './Header.css'

type PageView = 'chat' | 'redis-benefits'

interface HeaderProps {
  currentPage: PageView
  onPageChange: (page: PageView) => void
}

export default function Header({ currentPage, onPageChange }: HeaderProps) {
  const { username, logout } = useAuth()

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
