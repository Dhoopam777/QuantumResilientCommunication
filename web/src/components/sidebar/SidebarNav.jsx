import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/test/chat', label: 'Chats', icon: '💬', end: true },
  { to: '/test/requests', label: 'Requests', icon: '📩' },
  { to: '/test/friends', label: 'Friends', icon: '👥', disabled: true },
  { to: '/test/groups', label: 'Groups', icon: '👨‍👩‍👧‍👦', disabled: true },
  { to: '/test/ai', label: 'AI', icon: '🤖', disabled: true },
  { to: '/test/settings', label: 'Settings', icon: '⚙️', disabled: true },
  { to: '/test/profile', label: 'Profile', icon: '👤' },
]

export default function SidebarNav() {
  return (
    <nav className="flex-1 overflow-y-auto py-2">
      {navItems.map((item) => (
        item.disabled ? (
          <div
            key={item.to}
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-text-muted cursor-not-allowed opacity-50"
            title="Coming soon"
          >
            <span className="text-lg w-6 text-center">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-accent-soft text-accent font-medium'
                  : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
              }`
            }
          >
            <span className="text-lg w-6 text-center">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        )
      ))}
    </nav>
  )
}