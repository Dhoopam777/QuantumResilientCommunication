import { Link } from 'react-router-dom'
import Avatar from '../common/Avatar'
import ThemeToggle from '../common/ThemeToggle'
import { LogoutIcon } from '../icons'

export default function SidebarUserCard({ user, onLogout }) {
  return (
    <div className="border-t border-border/70 p-3 flex items-center gap-1.5">
      <Link
        to="/test/profile"
        className="group flex items-center gap-3 flex-1 min-w-0 rounded-lg px-1.5 py-1.5 transition-colors hover:bg-surface-hover"
      >
        <Avatar
          name={user?.display_name || user?.username}
          src={user?.profile_picture_url}
          size="sm"
          online={user?.is_online}
          ring
        />
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text-primary truncate transition-colors group-hover:text-accent">
            {user?.display_name || user?.username}
          </div>
          <div className="text-[11px] text-text-muted truncate">@{user?.username}</div>
        </div>
      </Link>
      <ThemeToggle />
      <button
        onClick={onLogout}
        className="icon-btn"
        aria-label="Logout"
        title="Logout"
      >
        <LogoutIcon className="w-[18px] h-[18px]" />
      </button>
    </div>
  )
}