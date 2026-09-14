import Sidebar from '../sidebar/Sidebar'

export default function ChatLayout({
  user,
  onLogout,
  search,
  onSearchChange,
  sidebarContent,
  children,
  detailsPanel,
  showSidebar = true,
  showDetails = false,
}) {
  return (
    <div className="h-screen flex overflow-hidden page-enter">
      {showSidebar && (
        <Sidebar user={user} onLogout={onLogout} search={search} onSearchChange={onSearchChange}>
          {sidebarContent}
        </Sidebar>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        {children}
      </div>
      {showDetails && detailsPanel}
    </div>
  )
}