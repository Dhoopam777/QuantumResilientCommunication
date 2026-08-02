import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from './common/ThemeToggle'

export default function Layout({ children }) {
  const { isLoggedIn, user, logout } = useAuth()

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
    </div>
  )
}