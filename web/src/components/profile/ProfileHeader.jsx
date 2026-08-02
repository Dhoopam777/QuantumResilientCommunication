import Avatar from '../common/Avatar'

export default function ProfileHeader({ user }) {
  return (
    <div className="flex items-center gap-4 p-4 border-b border-border">
      <Avatar
        name={user?.display_name || user?.username}
        src={user?.profile_picture_url}
        size="xl"
        online={user?.is_online}
      />
      <div className="flex-1 min-w-0">
        <h2 className="text-xl font-bold text-text-primary truncate">
          {user?.display_name || user?.username}
        </h2>
        <p className="text-sm text-text-muted">@{user?.username}</p>
        {user?.status_message && (
          <p className="text-sm text-text-secondary mt-1">• {user.status_message}</p>
        )}
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-xs px-2 py-0.5 rounded ${user?.is_online ? 'bg-accent-soft text-success' : 'bg-surface-hover text-text-muted'}`}>
            {user?.is_online ? 'Online' : 'Offline'}
          </span>
          {user?.last_seen && (
            <span className="text-xs text-text-muted">
              Last seen: {new Date(user.last_seen).toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}