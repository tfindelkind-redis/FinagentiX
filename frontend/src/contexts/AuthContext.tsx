import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

// Types
interface AuthState {
  isAuthenticated: boolean
  username: string | null
  token: string | null
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<boolean>
}

interface LoginResponse {
  token: string
  token_type: string
  expires_in: number
  username: string
}

// Get API base URL
const getApiBaseUrl = () => {
  const runtimeUrl = typeof window !== 'undefined' 
    ? (window as any).__ENV__?.PUBLIC_API_BASE_URL 
    : undefined
  return runtimeUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000'
}

// Local storage keys
const TOKEN_KEY = 'finagentix_token'
const USERNAME_KEY = 'finagentix_username'

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    username: null,
    token: null,
    isLoading: true,
  })

  // Load saved auth state on mount
  useEffect(() => {
    const loadSavedAuth = async () => {
      const savedToken = localStorage.getItem(TOKEN_KEY)
      const savedUsername = localStorage.getItem(USERNAME_KEY)

      if (savedToken && savedUsername) {
        // Verify token is still valid
        const isValid = await verifyToken(savedToken)
        if (isValid) {
          setAuthState({
            isAuthenticated: true,
            username: savedUsername,
            token: savedToken,
            isLoading: false,
          })
          return
        } else {
          // Token expired, clear storage
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(USERNAME_KEY)
        }
      }

      setAuthState(prev => ({ ...prev, isLoading: false }))
    }

    loadSavedAuth()
  }, [])

  // Verify token with API
  const verifyToken = async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      return response.ok
    } catch {
      return false
    }
  }

  // Login function
  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        return false
      }

      const data: LoginResponse = await response.json()

      // Save to localStorage
      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USERNAME_KEY, data.username)

      // Update state
      setAuthState({
        isAuthenticated: true,
        username: data.username,
        token: data.token,
        isLoading: false,
      })

      return true
    } catch (error) {
      console.error('Login error:', error)
      return false
    }
  }

  // Logout function
  const logout = () => {
    // Clear localStorage
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USERNAME_KEY)

    // Update state
    setAuthState({
      isAuthenticated: false,
      username: null,
      token: null,
      isLoading: false,
    })
  }

  // Check auth status
  const checkAuth = async (): Promise<boolean> => {
    if (!authState.token) {
      return false
    }
    return verifyToken(authState.token)
  }

  return (
    <AuthContext.Provider
      value={{
        ...authState,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// Hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Get current token (for API calls)
export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
