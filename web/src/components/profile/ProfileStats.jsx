export default function ProfileStats({ user }) {
  return (
    <div className="p-4 border-t border-border">
      <h3 className="text-xs font-semibold text-text-muted uppercase mb-2">Account</h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-text-muted">Email</span>
          <span className="text-text-primary">{user?.email}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Member since</span>
          <span className="text-text-primary">
            {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Verified</span>
          <span className={user?.is_verified ? 'text-success' : 'text-warning'}>
            {user?.is_verified ? '✓ Verified' : 'Not verified'}
          </span>
        </div>
      </div>
    </div>
  )
}