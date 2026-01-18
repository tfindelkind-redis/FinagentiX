import { Activity, MessageSquare, Zap } from 'lucide-react'
import CacheControls from './CacheControls'
import './Header.css'

type PageView = 'chat' | 'redis-benefits'

interface HeaderProps {
  currentPage: PageView
  onPageChange: (page: PageView) => void
}

export default function Header({ currentPage, onPageChange }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <div className="header-title">
            <Activity size={28} className="header-icon" />
            <h1>FinagentiX</h1>
            <span className="header-subtitle">AI Financial Assistant</span>
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
        </div>
      </div>
    </header>
  )
}
