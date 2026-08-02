import { Link } from 'react-router-dom'
import Avatar from '../common/Avatar'
import ThemeToggle from '../common/ThemeToggle'

export default function SidebarUserCard({ user, onLogout }) {
  return (
    <div className="border-t border-border p-3 flex items-center gap-2">
      <Link to="/test/profile" className="flex items-center gap-3 flex-1 min-w-0 hover:opacity-80">
        <Avatar
          name={user?.display_name || user?.username}
          src={user?.profile_picture_url}
          size="sm"
          online={user?.is_online}
        />
        <div className="min-w-0">
          <div className="text-sm font-medium text-text-primary truncate">
            {user?.display_name || user?.username}
          </div>
          <div className="text-xs text-text-muted truncate">@{user?.username}</div>
        </div>
      </Link>
      <ThemeToggle />
      <button
        onClick={onLogout}
        className="icon-btn"
        aria-label="Logout"
        title="Logout"
      >
        🚪
      </button>
    </div>
  )
}