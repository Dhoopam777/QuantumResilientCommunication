import { useState } from 'react'
import Avatar from '../common/Avatar'
import IconButton from '../common/IconButton'
import { CloseIcon, ShieldCheckIcon, SendIcon } from '../icons'
import { useChat } from '../../context/ChatContext'

export default function DetailsPanel({ conversation, currentUserId, canManage = false, onAddMember, onRemoveMember }) {
  const { closeDetails } = useChat()
  const [memberUsername, setMemberUsername] = useState('')
  if (!conversation) return null

  let title = 'Direct Message'
  let username = ''
  let avatarSrc = null
  let isOnline = false
  let bio = ''
  let statusMessage = ''

  if (conversation.is_group) {
    title = conversation.group_name || 'Group'
  } else {
    const other = conversation.participants?.find((p) => p.user_id !== currentUserId)
    title = other?.display_name || other?.username || 'Direct Message'
    username = other ? `@${other.username}` : ''
    avatarSrc = other?.profile_picture_url
    isOnline = other?.is_online || false
    bio = other?.bio || ''
    statusMessage = other?.status_message || ''
  }

  return (
    <div className="w-72 flex-shrink-0 border-l border-border flex flex-col h-full overflow-y-auto bg-surface/90 backdrop-blur-md">
      <div className="p-4 border-b border-border flex items-center justify-between sticky top-0 bg-surface/80 backdrop-blur-md z-10">
        <h3 className="font-semibold text-sm text-text-primary">Details</h3>
        <button type="button" onClick={closeDetails} className="icon-btn" aria-label="Close details" title="Close details">
          <CloseIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Profile info */}
      <div className="p-4 flex flex-col items-center text-center border-b border-border">
        <Avatar name={title} src={avatarSrc} size="xl" online={isOnline} />
        <h4 className="mt-3 font-semibold text-text-primary">{title}</h4>
        {username && <p className="text-sm text-text-muted">{username}</p>}
        {statusMessage && <p className="text-sm text-text-secondary mt-1">• {statusMessage}</p>}
        {bio && <p className="text-sm text-text-secondary mt-2">{bio}</p>}
        {conversation.is_encrypted && (
          <p className="inline-flex items-center gap-1 text-xs text-success mt-3 px-2.5 py-1 rounded-full bg-success/10">
            <ShieldCheckIcon className="w-3.5 h-3.5" /> End-to-end encrypted
          </p>
        )}
      </div>

      {/* Shared media placeholder */}
      <div className="p-4 border-b border-border">
        <h5 className="text-xs font-semibold text-text-muted uppercase mb-2">Shared Media</h5>
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="aspect-square bg-surface-hover rounded-lg flex items-center justify-center text-text-muted text-xs">
              {i}
            </div>
          ))}
        </div>
        <p className="text-xs text-text-muted mt-2 text-center">Media sharing coming soon</p>
      </div>

      {/* Group members placeholder */}
      {conversation.is_group && (
        <div className="p-4 border-b border-border">
          <h5 className="text-xs font-semibold text-text-muted uppercase mb-2">
            Members ({conversation.participants?.length || 0})
          </h5>
          <div className="space-y-2">
            {conversation.participants?.map((p) => (
              <div key={p.id} className="flex items-center gap-2">
                <Avatar name={p.display_name || p.username} src={p.profile_picture_url} size="sm" online={p.is_online} />
                <div className="min-w-0">
                  <div className="text-sm text-text-primary truncate">{p.display_name || p.username}</div>
                  <div className="text-xs text-text-muted truncate">@{p.username}</div>
                </div>
                {p.user_id === conversation.created_by && (
                  <span className="text-[10px] text-accent ml-auto">Owner</span>
                )}
                {canManage && p.user_id !== conversation.created_by && (
                  <button
                    type="button"
                    className="text-xs text-danger hover:underline"
                    onClick={() => onRemoveMember?.(p.username)}
                    title={`Remove @${p.username}`}
                  >
                    Remove
                  </button>
                )}
                </div>
            ))}
          </div>
          {canManage && (
            <form
                className="mt-3 flex gap-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (memberUsername.trim()) {
                    onAddMember?.(memberUsername.trim())
                    setMemberUsername('')
                  }
                }}
            >
                <input
                  className="input min-w-0 text-xs"
                  placeholder="Username"
                  value={memberUsername}
                  onChange={(event) => setMemberUsername(event.target.value)}
                  maxLength={50}
                />
                <button type="submit" className="btn-secondary text-xs"><SendIcon className="w-3 h-3" />Add</button>
            </form>
          )}
        </div>
      )}

      {/* Files placeholder */}
      <div className="p-4">
        <h5 className="text-xs font-semibold text-text-muted uppercase mb-2">Files</h5>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-2 p-2 bg-surface-hover rounded-lg">
              <span className="text-lg">📄</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-text-primary truncate">file_{i}.pdf</div>
                <div className="text-[10px] text-text-muted">File sharing coming soon</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}