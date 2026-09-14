import SidebarNav from './SidebarNav'
import SidebarSearch from './SidebarSearch'
import SidebarUserCard from './SidebarUserCard'
import { ShieldIcon, LockIcon } from '../icons'

export default function Sidebar({ user, onLogout, search, onSearchChange, children }) {
  return (
    <aside className="w-64 flex-shrink-0 border-r border-border flex flex-col h-full overflow-hidden bg-surface/90 backdrop-blur-2xl panel-enter">
      {/* Brand header */}
      <div className="px-4 pt-4 pb-3 flex items-center gap-2.5">
        <span className="brand-mark">
          <ShieldIcon width="1.1em" height="1.1em" />
        </span>
        <div className="min-w-0">
          <div className="text-sm font-bold tracking-tight text-text-primary leading-none">
            QRC Secure
          </div>
          <div className="mt-1 flex items-center gap-1 text-[9px] font-medium uppercase tracking-[0.16em] text-text-muted">
            <LockIcon width="0.85em" height="0.85em" />
            Quantum · Private
          </div>
        </div>
      </div>

      <SidebarSearch value={search} onChange={onSearchChange} />

      <div className="flex-1 flex flex-col min-h-0">
        <SidebarNav />
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {children}
        </div>
      </div>

      <SidebarUserCard user={user} onLogout={onLogout} />
    </aside>
  )
}