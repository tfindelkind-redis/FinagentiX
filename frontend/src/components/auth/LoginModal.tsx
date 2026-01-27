import { useState, FormEvent } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { Lock, User, AlertCircle, Loader2, Activity } from 'lucide-react'
import './LoginModal.css'

export default function LoginModal() {
  const { login, isLoading: authLoading } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const success = await login(username, password)
      if (!success) {
        setError('Invalid username or password')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="login-modal-overlay">
        <div className="login-modal">
          <div className="login-loading">
            <Loader2 className="spin" size={32} />
            <p>Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="login-modal-overlay">
      <div className="login-modal">
        <div className="login-header">
          <div className="login-logo">
            <Activity size={40} className="login-icon" />
          </div>
          <h1>FinagentiX</h1>
          <p className="login-subtitle">AI Financial Trading Assistant</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="login-field">
            <label htmlFor="username">
              <User size={16} />
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">
              <Lock size={16} />
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              autoComplete="current-password"
            />
          </div>

          <button 
            type="submit" 
            className="login-button"
            disabled={isSubmitting || !username || !password}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="spin" size={18} />
                Signing in...
              </>
            ) : (
              <>
                <Lock size={18} />
                Sign In
              </>
            )}
          </button>
        </form>

        <div className="login-footer">
          <p className="login-demo-note">
            🔒 Demo Environment - Contact admin for credentials
          </p>
        </div>
      </div>
    </div>
  )
}
