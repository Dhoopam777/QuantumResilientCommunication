import SidebarNav from './SidebarNav'
import SidebarSearch from './SidebarSearch'
import SidebarUserCard from './SidebarUserCard'

export default function Sidebar({ user, onLogout, search, onSearchChange, children }) {
  return (
    <aside className="w-64 flex-shrink-0 bg-surface border-r border-border flex flex-col h-full">
      <SidebarSearch value={search} onChange={onSearchChange} />
      <SidebarNav />
      {children}
      <SidebarUserCard user={user} onLogout={onLogout} />
    </aside>
  )
}