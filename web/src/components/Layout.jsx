import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../lib/api'
import { useState } from 'react'
import ThemeToggle from './common/ThemeToggle'
import { ShieldIcon, ChatIcon, LogoutIcon } from './icons'

export default function Layout({ children }) {
  const { isLoggedIn, user, logout } = useAuth()
  const [resendState, setResendState] = useState('')
  const unverified = isLoggedIn && user && !(user.is_email_verified || user.is_verified)

  const resend = async () => {
    const response = await authApi.resendVerification(user?.email)
    setResendState(response.status === 200 ? 'Verification email sent.' : (response.data?.detail || 'Unable to resend.'))
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-surface/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <Link to="/test" className="group flex items-center gap-2.5">
            <span className="brand-mark">
              <ShieldIcon width="1.1em" height="1.1em" />
            </span>
            <span className="text-base font-bold tracking-tight text-text-primary transition-colors group-hover:text-accent">
              QRC
            </span>
          </Link>
          <div className="flex items-center gap-1.5">
            {isLoggedIn && user && (
              <Link to="/test/chat" className="btn-ghost text-sm">
                <ChatIcon className="w-4 h-4" />
                Go to Chat
              </Link>
            )}
            <ThemeToggle />
            {isLoggedIn && (
              <button onClick={logout} className="btn-ghost text-sm text-danger hover:!text-danger">
                <LogoutIcon className="w-4 h-4" />
                Logout
              </button>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 page-enter">{children}</main>
      {unverified && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-xl card shadow-popover p-4 panel-enter">
          <p className="text-sm text-text-primary">Verify your email to unlock messaging and groups.</p>
          <button type="button" className="btn-secondary mt-2 text-sm" onClick={resend}>Resend verification email</button>
          {resendState && <p className="text-xs text-text-muted mt-2">{resendState}</p>}
        </div>
      )}
    </div>
  )
}