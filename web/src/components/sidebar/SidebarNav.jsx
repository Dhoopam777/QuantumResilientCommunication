import { NavLink } from 'react-router-dom'
import { ChatIcon, InboxIcon, UserPlusIcon, UsersIcon, SparkIcon, SettingsIcon, ProfileIcon } from '../icons'

const navItems = [
  { to: '/test/chat', label: 'Chats', icon: ChatIcon, end: true },
  { to: '/test/requests', label: 'Requests', icon: InboxIcon },
  { to: '/test/friends', label: 'Friends', icon: UserPlusIcon, disabled: true },
  { to: '/test/groups', label: 'Groups', icon: UsersIcon },
  { to: '/test/ai', label: 'AI', icon: SparkIcon, disabled: true },
  { to: '/test/settings', label: 'Settings', icon: SettingsIcon, disabled: true },
  { to: '/test/profile', label: 'Profile', icon: ProfileIcon },
]

export default function SidebarNav() {
  return (
    <nav className="shrink-0 px-2 pb-2" aria-label="Main navigation">
      <p className="section-label">Main</p>
      <div className="space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon
          if (item.disabled) {
            return (
              <div
                key={item.to}
                className="nav-item-disabled"
                title="Coming soon"
                aria-disabled="true"
              >
                <Icon className="w-[18px] h-[18px] shrink-0" />
                <span className="flex-1 truncate">{item.label}</span>
                <span className="coming-soon">Soon</span>
              </div>
            )
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon className="w-[18px] h-[18px] shrink-0" />
              <span className="flex-1 truncate">{item.label}</span>
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}