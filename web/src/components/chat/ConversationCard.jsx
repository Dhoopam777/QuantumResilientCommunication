import { Link } from 'react-router-dom'
import Avatar from '../common/Avatar'
import Badge from '../common/Badge'

function relativeTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'now'
  if (diffMin < 60) return `${diffMin}m`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d`
  return date.toLocaleDateString()
}

export default function ConversationCard({ conversation, currentUserId, isActive = false, unreadCount = 0 }) {
  // Determine display info
  let title = 'Direct Message'
  let subtitle = ''
  let avatarSrc = null
  let isOnline = false

  if (conversation.is_group) {
    title = conversation.group_name || 'Group'
    subtitle = `${conversation.participants?.length || 0} participants`
  } else {
    const other = conversation.participants?.find((p) => p.user_id !== currentUserId)
    title = other?.display_name || other?.username || 'Direct Message'
    subtitle = other ? `@${other.username}` : ''
    avatarSrc = other?.profile_picture_url
    isOnline = other?.is_online || false
  }

  const lastMsg = conversation.last_message

  return (
    <Link
      to={`/test/chat/${conversation.id}`}
      className={`flex items-start gap-3 px-4 py-3 transition-colors ${
        isActive
          ? 'bg-accent-soft'
          : 'hover:bg-surface-hover'
      }`}
    >
      <Avatar name={title} src={avatarSrc} size="md" online={isOnline} />
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center gap-2">
          <span className="font-medium text-sm text-text-primary truncate">{title}</span>
          <span className="text-xs text-text-muted flex-shrink-0">
            {lastMsg ? relativeTime(lastMsg.created_at) : relativeTime(conversation.updated_at)}
          </span>
        </div>
        {subtitle && (
          <div className="text-xs text-text-muted truncate">{subtitle}</div>
        )}
        <div className="flex justify-between items-center gap-2 mt-0.5">
          <span className="text-xs text-text-secondary truncate">
            {lastMsg ? (
              <>
                {lastMsg.message_type !== 'text' && (
                  <span className="text-text-muted mr-1">[{lastMsg.message_type}]</span>
                )}
                {lastMsg.content_encrypted}
              </>
            ) : (
              <span className="text-text-muted">No messages yet</span>
            )}
          </span>
          <Badge count={unreadCount} />
        </div>
      </div>
    </Link>
  )
}