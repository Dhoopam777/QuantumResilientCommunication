import { useState, useRef, useEffect } from 'react'

// Confirmation dialog for deletion mode selection
function DeleteConfirmationDialog({ isOpen, onDelete, onCancel, isSender }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-surface-elevated border border-border rounded-lg shadow-popover p-4 w-64">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Delete message?</h3>
        <button
          className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-surface-hover rounded-md mb-1"
          onClick={() => onDelete('me')}
        >
          Delete for Me
        </button>
        {isSender && (
          <button
            className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-900/20 rounded-md mb-1"
            onClick={() => onDelete('everyone')}
          >
            Delete for Everyone
          </button>
        )}
        <button
          className="w-full text-left px-3 py-2 text-sm text-text-muted hover:bg-surface-hover rounded-md"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function MessageBubble({
  message,
  isOutgoing,
  onReply,
  onScrollToMessage,
  onEdit,
  onDelete,
  isEditing,
  onStartEdit,
  onCancelEdit,
  onReact,
  currentUserId,
}) {
  const [editContent, setEditContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [editError, setEditError] = useState(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showReactionPicker, setShowReactionPicker] = useState(false)
  const editInputRef = useRef(null)

  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  const editedTime = message.edited_at
    ? new Date(message.edited_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  // Determine if this message is deleted (soft-deleted for all, or deleted for me by current user)
  const isDeletedForMe =
    message.is_deleted ||
    (message.deleted_at && message.deleted_by && message.delete_type === 'me')

  // Initialize edit content when editing starts
  useEffect(() => {
    if (isEditing) {
      setEditContent(message.content_encrypted || '')
      setEditError(null)
      // Focus the textarea after render
      setTimeout(() => editInputRef.current?.focus(), 0)
    }
  }, [isEditing, message.id, message.content_encrypted])

  const handleReplyClick = () => {
    if (onReply) onReply(message)
  }

  const handleReplyPreviewClick = () => {
    if (onScrollToMessage && message.reply_preview) {
      onScrollToMessage(message.reply_preview.id)
    }
  }

  const handleStartEdit = () => {
    if (onStartEdit) onStartEdit(message)
  }

  const handleCancelEdit = () => {
    if (onCancelEdit) onCancelEdit(message)
  }

  const handleSaveEdit = async () => {
    const trimmed = editContent.trim()
    if (!trimmed || isSaving) return
    if (trimmed === message.content_encrypted) {
      // No change — just cancel
      handleCancelEdit()
      return
    }
    setIsSaving(true)
    setEditError(null)
    try {
      await onEdit(message, trimmed)
      // onEdit handles closing the edit mode on success
    } catch (err) {
      setEditError(err?.message || 'Failed to save edit')
      setIsSaving(false)
    }
  }

  const handleEditKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSaveEdit()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      handleCancelEdit()
    }
  }

  const handleDeleteClick = () => {
    setShowDeleteDialog(true)
  }

  const handleDeleteConfirm = async (mode) => {
    setIsDeleting(true)
    setShowDeleteDialog(false)
    try {
      await onDelete(message, mode)
    } catch (err) {
      // Error handling is in the parent component
    } finally {
      setIsDeleting(false)
    }
  }

  const handleCancelDelete = () => {
    setShowDeleteDialog(false)
  }

  const handleReaction = async (emoji) => {
    if (!onReact) return
    setShowReactionPicker(false)
    await onReact(message, emoji)
  }

  // If the message is deleted for everyone, show placeholder
  if (message.is_deleted && message.delete_type === 'everyone') {
    return (
      <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}>
        <div
          className={`relative max-w-[70%] rounded-bubble px-3 py-2 text-sm shadow-card ${
            isOutgoing
              ? 'bg-bubble-outgoing text-white/50 rounded-br-sm'
              : 'bg-bubble-incoming text-text-muted rounded-bl-sm'
          }`}
        >
          <div className="italic">This message was deleted.</div>
          <div className={`flex items-center mt-1 text-[10px] ${isOutgoing ? 'text-white/50' : 'text-text-muted'}`}>
            <span>{time}</span>
          </div>
        </div>
      </div>
    )
  }

  // If deleted for me only, hide entirely (the requesting user doesn't see it)
  if (isDeletedForMe && message.delete_type === 'me') {
    return null
  }

  return (
    <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}>
      <div
        className={`relative max-w-[70%] rounded-bubble px-3 py-2 text-sm shadow-card ${
          isOutgoing
            ? 'bg-bubble-outgoing text-white rounded-br-sm'
            : 'bg-bubble-incoming text-text-primary rounded-bl-sm'
        }`}
      >
        {/* Reply preview indicator */}
        {message.reply_preview && (
          <button
            onClick={handleReplyPreviewClick}
            className={`block w-full text-left mb-1.5 rounded-md px-2 py-1 text-xs border-l-2 ${
              isOutgoing
                ? 'bg-white/10 border-white/50 text-white/80 hover:bg-white/20'
                : 'bg-surface-elevated border-primary text-text-muted hover:bg-surface-hover'
            }`}
            title="Click to view original message"
          >
            <span className="font-semibold block truncate">
              {message.reply_preview.is_deleted ? 'Deleted message' : '↩️ Reply'}
            </span>
            <span className="block truncate opacity-80">
              {message.reply_preview.content_encrypted}
            </span>
          </button>
        )}

        {message.message_type !== 'text' && (
          <div className={`text-xs mb-1 ${isOutgoing ? 'text-white/80' : 'text-text-muted'}`}>
            [{message.message_type}]
          </div>
        )}

        {/* Edit mode */}
        {isEditing ? (
          <div className="flex flex-col gap-1">
            <textarea
              ref={editInputRef}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              onKeyDown={handleEditKeyDown}
              className={`input-base w-full resize-none text-sm ${
                isOutgoing ? 'bg-white/10 text-white placeholder-white/50' : 'bg-surface-elevated text-text-primary'
              }`}
              rows={2}
              disabled={isSaving}
              aria-label="Edit message"
            />
            {editError && (
              <div className="text-xs text-red-400">{editError}</div>
            )}
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={handleSaveEdit}
                disabled={!editContent.trim() || isSaving}
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  isOutgoing
                    ? 'bg-white/20 text-white hover:bg-white/30 disabled:opacity-50'
                    : 'bg-primary text-white hover:bg-primary-dark disabled:opacity-50'
                }`}
                aria-label="Save edit"
              >
                {isSaving ? (
                  <span className="inline-flex items-center gap-1">
                    <span className="animate-spin inline-block w-3 h-3 border-2 border-white/50 border-t-white rounded-full" />
                    Saving...
                  </span>
                ) : (
                  'Save'
                )}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={isSaving}
                className={`px-2 py-0.5 rounded text-xs ${
                  isOutgoing ? 'text-white/70 hover:text-white' : 'text-text-muted hover:text-text-primary'
                }`}
                aria-label="Cancel edit"
              >
                Cancel
              </button>
              <span className={`text-[10px] ${isOutgoing ? 'text-white/50' : 'text-text-muted'}`}>
                Enter to save · Esc to cancel
              </span>
            </div>
          </div>
        ) : (
          <>
            <div className="break-words">{message.content_encrypted}</div>
            {message.attachments?.length > 0 && (
              <div className="mt-2 space-y-2">
                {message.attachments.map((attachment) => (
                  <div key={attachment.id} className="rounded border border-white/20 p-1">
                    {attachment.local_url && attachment.mime_type?.startsWith('image/') ? (
                      <img
                        src={attachment.local_url}
                        alt={attachment.original_filename}
                        className="max-h-64 max-w-full rounded object-contain"
                      />
                    ) : attachment.local_url && attachment.mime_type?.startsWith('audio/') ? (
                      <audio controls preload="metadata" className="max-w-full" aria-label="Voice message">
                        <source src={attachment.local_url} type={attachment.mime_type} />
                        Your browser cannot play this voice message.
                      </audio>
                    ) : (
                      <span className="text-xs">{attachment.original_filename}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className={`flex items-center gap-1 mt-1 text-[10px] ${isOutgoing ? 'text-white/70' : 'text-text-muted'}`}>
              <span>{time}</span>
              {message.is_edited && (
                <span title={editedTime ? `Edited at ${editedTime}` : 'Edited'}>• Edited</span>
              )}
              {message.signature_status === 'verified' && <span title="Verified message">• Verified ✓</span>}
              {message.signature_status === 'failed' && <span title="Message verification failed">• Verification Failed</span>}
              {isOutgoing && <span>• ✓</span>}
            </div>
          </>
        )}

        {/* Hover actions: react, reply, forward, edit, delete */}
        {!isEditing && (
          <div className="hidden group-hover:flex absolute -top-3 right-0 bg-surface-elevated border border-border rounded-lg shadow-popover px-1 py-0.5 gap-0.5">
            <button
              className="icon-btn !p-1 text-xs"
              title="React"
              aria-label="React"
              onClick={() => setShowReactionPicker((visible) => !visible)}
            >🙂</button>
            <button
              className="icon-btn !p-1 text-xs"
              title="Reply"
              aria-label="Reply"
              onClick={handleReplyClick}
            >
              ↩️
            </button>
            <button className="icon-btn !p-1 text-xs" title="Forward" aria-label="Forward">➡️</button>
            {isOutgoing && message.message_type !== 'system' && (
              <button
                className="icon-btn !p-1 text-xs"
                title="Edit"
                aria-label="Edit message"
                onClick={handleStartEdit}
              >
                ✏️
              </button>
            )}
            <button
              className="icon-btn !p-1 text-xs"
              title="Delete"
              aria-label="Delete"
              onClick={handleDeleteClick}
              disabled={isDeleting}
            >
              🗑️
            </button>
          </div>
        )}

        {showReactionPicker && (
          <div className="absolute z-10 -top-12 right-0 flex gap-1 rounded-lg border border-border bg-surface-elevated p-1 shadow-popover">
            {['👍', '❤️', '😂', '😮', '😢', '🙏', '🔥', '👎'].map((emoji) => (
              <button
                key={emoji}
                className="rounded p-1 text-base hover:bg-surface-hover"
                title={`React with ${emoji}`}
                onClick={() => handleReaction(emoji)}
              >{emoji}</button>
            ))}
          </div>
        )}

        {message.reactions?.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {message.reactions.map((reaction) => (
              <button
                key={reaction.emoji}
                onClick={() => handleReaction(reaction.emoji)}
                className={`rounded-full border px-1.5 py-0.5 text-[11px] ${
                  reaction.reacted_by_me ? 'border-primary bg-primary/20' : 'border-border bg-surface-elevated'
                }`}
                title={`Reacted by ${reaction.users?.slice(0, 2).map((u) => u.name).join(', ')}${
                  reaction.count > 2 ? ` and ${reaction.count - 2} others` : ''
                }`}
              >
                {reaction.emoji} {reaction.count}
              </button>
            ))}
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        <DeleteConfirmationDialog
          isOpen={showDeleteDialog}
          isSender={isOutgoing}
          onDelete={handleDeleteConfirm}
          onCancel={handleCancelDelete}
        />
      </div>
    </div>
  )
}
