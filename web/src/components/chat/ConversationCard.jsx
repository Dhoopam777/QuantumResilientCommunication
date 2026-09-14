import Avatar from '../common/Avatar'
import Badge from '../common/Badge'
import { LockIcon, ImageIcon, VoiceIcon, FileIcon } from '../icons'
import { useChat } from '../../context/ChatContext'

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

// Privacy: never reveal email addresses or UUIDs in the Recent Chats UI.
// A display name is free-form user input; scrub it defensively at the
// presentation layer (schema already omits email addresses).
function sanitizeText(value) {
  if (!value) return value
  const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi
  const emailPattern = /[\\w.+-]+@[\\w.-]+\.[A-Za-z]{2,}/g
  return String(value).replace(uuidPattern, '[id]').replace(emailPattern, '[email]')
}

// Message preview shown in the recent-chats list.
// The conversation list has NO decrypted content (decryption only happens in
// the open chat after a secure session is established), so the ONLY safe value
// to display for encrypted messages is a human label — never ciphertext.
function messagePreview(lastMsg) {
  if (!lastMsg) return { text: 'No messages yet', icon: null }
  const type = lastMsg.message_type
  if (type === 'image') return { text: 'Photo', icon: <ImageIcon className="w-3 h-3" /> }
  if (type === 'audio') return { text: 'Voice message', icon: <VoiceIcon className="w-3 h-3" /> }
  if (type === 'file') return { text: 'File', icon: <FileIcon className="w-3 h-3" /> }
  if (type === 'system') return { text: 'System event', icon: null }
  return { text: 'Encrypted message', icon: null }
}

export default function ConversationCard({ conversation, currentUserId, isActive = false, style }) {
  const { selectConversation, unreadCounts, resetUnread } = useChat()
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
  const isEncrypted = Boolean(conversation.is_encrypted)
  const preview = messagePreview(lastMsg)
  const safeTitle = sanitizeText(title)
  const safeSubtitle = sanitizeText(subtitle)
  const unread = unreadCounts[conversation.id] || 0

  return (
    <button
      type="button"
      onClick={() => {
        selectConversation(conversation.id)
        resetUnread(conversation.id)
      }}
      style={style}
      aria-pressed={isActive}
      className={`group item-enter flex w-full items-start gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-200 ${
        isActive ? 'bg-accent-soft border-accent/30' : 'hover:bg-surface-hover active:scale-[0.995]'
      }`}
    >
      <Avatar name={safeTitle} src={avatarSrc} size="md" online={isOnline} />
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center gap-2">
          <span className={`font-semibold text-sm truncate ${isActive ? 'text-accent' : 'text-text-primary'}`}>
            {safeTitle}
          </span>
          <span className="text-[10px] font-medium text-text-muted flex-shrink-0">
            {lastMsg ? relativeTime(lastMsg.created_at) : relativeTime(conversation.updated_at)}
          </span>
        </div>
        {safeSubtitle && (
          <div className="text-xs text-text-muted truncate">{safeSubtitle}</div>
        )}
        <div className="flex justify-between items-center gap-2 mt-1.5">
          <span className="flex items-center gap-1 text-xs text-text-secondary truncate">
            {isEncrypted && (
              <LockIcon className="w-3 h-3 text-text-muted shrink-0" />
            )}
            {preview.icon}
            <span className="truncate">{preview.text}</span>
          </span>
          <Badge count={unread} className="mt-0.5">
            {unread}
          </Badge>
        </div>
      </div>
    </button>
  )
}