import Avatar from '../common/Avatar'
import IconButton from '../common/IconButton'
import { ShieldCheckIcon, InfoIcon } from '../icons'
import { useChat } from '../../context/ChatContext'

export default function ChatHeader({ conversation, currentUserId }) {
  const { openDetails } = useChat()
  if (!conversation) {
    return (
      <div className="h-16 border-b border-border flex items-center px-4 bg-surface/60 backdrop-blur-md">
        <span className="text-sm text-text-muted">Select a conversation</span>
      </div>
    )
  }

  let title = 'Direct Message'
  let subtitle = ''
  let avatarSrc = null
  let isOnline = false
  let statusMessage = ''

  if (conversation.is_group) {
    title = conversation.group_name || 'Group'
    subtitle = `${conversation.participants?.length || 0} participants`
  } else {
    const other = conversation.participants?.find((p) => p.user_id !== currentUserId)
    title = other?.display_name || other?.username || 'Direct Message'
    subtitle = other ? `@${other.username}` : ''
    avatarSrc = other?.profile_picture_url
    isOnline = other?.is_online || false
    statusMessage = other?.status_message || ''
  }

  return (
    <div className="h-16 border-b border-border flex items-center px-4 gap-3 flex-shrink-0 bg-surface/60 backdrop-blur-md">
      <Avatar name={title} src={avatarSrc} size="md" online={isOnline} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-text-primary truncate">{title}</span>
          {conversation.is_encrypted && (
            <span className="text-xs text-success inline-flex items-center gap-0.5" title="End-to-end encrypted">
              <ShieldCheckIcon className="w-3.5 h-3.5" />
            </span>
          )}
        </div>
        {subtitle && <div className="text-xs text-text-muted truncate">{subtitle}</div>}
        {statusMessage && !conversation.is_group && (
          <div className="text-xs text-text-secondary truncate">• {statusMessage}</div>
        )}
      </div>
      <button type="button" onClick={openDetails} className="icon-btn" aria-label="View details" title="View details">
        <InfoIcon className="w-5 h-5" />
      </button>
    </div>
  )
}