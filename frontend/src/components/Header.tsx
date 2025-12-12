import { Activity } from 'lucide-react'
import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title">
          <Activity size={28} className="header-icon" />
          <h1>FinagentiX</h1>
          <span className="header-subtitle">AI Financial Assistant</span>
        </div>
        <div className="header-status">
          <div className="status-indicator">
            <span className="status-dot status-online"></span>
            <span className="status-text">Online</span>
          </div>
        </div>
      </div>
    </header>
  )
}
