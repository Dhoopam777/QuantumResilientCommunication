import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/test/register', label: 'Register', auth: false },
  { to: '/test/login', label: 'Login', auth: false },
  { to: '/test/dashboard', label: 'Dashboard', auth: true },
  { to: '/test/conversations', label: 'Conversations', auth: true },
  { to: '/test/conversations/new', label: 'New Conversation', auth: true },
  { to: '/test/profile', label: 'Profile', auth: true },
  { to: '/test/tokens', label: 'Token Viewer', auth: true },
]

export default function Layout({ children }) {
  const { isLoggedIn, user, logout } = useAuth()
  const location = useLocation()

  // Generate initials for avatar fallback
  const initials = (user?.display_name || user?.username || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/test" className="text-lg font-bold text-gray-800">
            QRC Test UI
          </Link>
          <div className="flex items-center gap-3">
            {isLoggedIn && user && (
              <Link to="/test/profile" className="flex items-center gap-2 hover:opacity-80">
                {user.profile_picture_url ? (
                  <img
                    src={user.profile_picture_url}
                    alt="Profile"
                    className="w-7 h-7 rounded-full object-cover border"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                    {initials}
                  </div>
                )}
                <span className="text-sm text-gray-700">
                  {user.display_name || user.username}
                </span>
              </Link>
            )}
            <span className={`text-xs px-2 py-1 rounded ${isLoggedIn ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {isLoggedIn ? 'Authenticated' : 'Not logged in'}
            </span>
            {isLoggedIn && (
              <button onClick={logout} className="text-sm text-red-600 hover:underline">
                Logout
              </button>
            )}
          </div>
        </div>
        <nav className="max-w-4xl mx-auto px-4 pb-3 flex flex-wrap gap-2">
          {navItems
            .filter((item) => !item.auth || isLoggedIn)
            .map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`text-sm px-3 py-1 rounded ${
                  location.pathname === item.to
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {item.label}
              </Link>
            ))}
        </nav>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-6">{children}</main>
    </div>
  )
}