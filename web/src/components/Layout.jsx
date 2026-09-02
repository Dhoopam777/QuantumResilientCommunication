import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../lib/api'
import { useState } from 'react'
import ThemeToggle from './common/ThemeToggle'

export default function Layout({ children }) {
  const { isLoggedIn, user, logout } = useAuth()
  const [resendState, setResendState] = useState('')
  const unverified = isLoggedIn && user && !(user.is_email_verified || user.is_verified)

  const resend = async () => {
    const response = await authApi.resendVerification(user?.email)
    setResendState(response.status === 200 ? 'Verification email sent.' : (response.data?.detail || 'Unable to resend.'))
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="bg-surface-elevated border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/test" className="text-lg font-bold text-text-primary">
            QRC
          </Link>
          <div className="flex items-center gap-3">
            {isLoggedIn && user && (
              <Link to="/test/chat" className="text-sm text-accent hover:underline">
                Go to Chat
              </Link>
            )}
            <ThemeToggle />
            {isLoggedIn && (
              <button onClick={logout} className="text-sm text-danger hover:underline">
                Logout
              </button>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6">{children}</main>
      {unverified && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-lg border border-warning bg-surface-elevated p-4 shadow-lg">
          <p className="text-sm text-text-primary">Verify your email to unlock messaging and groups.</p>
          <button type="button" className="btn-secondary mt-2 text-sm" onClick={resend}>Resend verification email</button>
          {resendState && <p className="text-xs text-text-muted mt-2">{resendState}</p>}
        </div>
      )}
    </div>
  )
}