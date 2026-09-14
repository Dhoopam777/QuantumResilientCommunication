import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  CheckIcon,
  CloseIcon,
  EditIcon,
  FileIcon,
  ForwardIcon,
  ImageIcon,
  LockIcon,
  MoreIcon,
  ReplyIcon,
  ShieldCheckIcon,
  VoiceIcon,
} from '../icons'

function ActionButton({ label, onClick, disabled = false, children, title, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title || label}
      aria-label={label}
      className={`icon-btn !w-7 !h-7 rounded-md text-[15px] ${className}`}
    >
      {children}
    </button>
  )
}

function SenderName({ name, isOutgoing }) {
  if (!name || isOutgoing) return null
  return <span className="block mb-1 text-[11px] font-semibold text-accent truncate">{name}</span>
}

function typeLabel(messageType) {
  switch (messageType) {
    case 'image': return 'Photo'
    case 'audio': return 'Voice message'
    case 'file': return 'File'
    case 'system': return 'System event'
    default: return 'Message'
  }
}

function TypeChip({ messageType, isOutgoing }) {
  if (messageType === 'text' || !messageType) return null
  const iconMap = {
    image: <ImageIcon className="w-3 h-3" />,
    audio: <VoiceIcon className="w-3 h-3" />,
    file: <FileIcon className="w-3 h-3" />,
  }
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium uppercase tracking-wide ${isOutgoing ? 'bg-white/15 text-white/90' : 'bg-accent-soft text-accent'
      }`}>
      {iconMap[messageType]}
      {typeLabel(messageType)}
    </span>
  )
}

const SENDER_STAGES = [
  { key: 'sender-plaintext', label: 'Plaintext Message', detail: 'The actual message starts in Alice\'s readable view.', algorithm: 'SOURCE', ready: (data) => Boolean(data.hasPlaintext) },
  { key: 'sender-encryption', label: 'AES-256-GCM Encryption', detail: 'Authenticated encryption protects the message content.', algorithm: 'SYMMETRIC ENCRYPTION', ready: (data) => data.encryptionReady },
  { key: 'sender-protection', label: 'ML-KEM-768 / ML-DSA-65 Protection', detail: 'The session protects key material and the sender signature is checked by the backend.', algorithm: 'POST-QUANTUM PROTECTION', ready: (data) => data.sessionReady && data.signatureStatus !== 'unavailable' },
  { key: 'sender-payload', label: 'Encrypted Payload', detail: 'Only the protected package crosses the transport boundary.', algorithm: 'PROTECTED DATA', ready: (data) => data.encryptionReady },
  { key: 'sender-sent', label: 'Message Sent', detail: 'Alice\'s protected message is handed to the network.', algorithm: 'TRANSPORT', ready: (data) => data.encryptionReady },
]

const RECEIVER_STAGES = [
  { key: 'receiver-received', label: 'Message Received', detail: 'Bob receives the protected message package.', algorithm: 'TRANSPORT', ready: (data) => data.encryptionReady },
  { key: 'receiver-verification', label: 'ML-DSA-65 / SHA-256 Verification', detail: 'Bob verifies sender authenticity and message integrity using the real backend results.', algorithm: 'AUTHENTICITY + INTEGRITY', ready: (data) => data.signatureStatus !== 'unavailable' || data.integrityStatus !== 'unavailable' },
  { key: 'receiver-decryption', label: 'AES-256-GCM Decryption', detail: 'The authenticated payload is opened for Bob.', algorithm: 'SYMMETRIC DECRYPTION', ready: (data) => data.encryptionReady && data.integrityStatus === 'verified' },
  { key: 'receiver-plaintext', label: 'Plaintext Message', detail: 'The verified message is readable by Bob.', algorithm: 'SECURE RESULT', ready: (data) => Boolean(data.hasPlaintext && data.integrityStatus === 'verified') },
]

function securityStatus(value) {
  if (value === 'verified') return 'verified'
  if (value === 'invalid' || value === 'failed') return 'invalid'
  return 'unavailable'
}

function SecurityFlowModal({ isOpen, onClose, message, sessionReady, isOutgoing }) {
  const [animationTick, setAnimationTick] = useState(0)
  const flowStages = [...SENDER_STAGES, ...RECEIVER_STAGES]

  useEffect(() => {
    if (!isOpen) return undefined
    setAnimationTick(0)
    const totalTicks = flowStages.length * 3
    const timer = window.setInterval(() => {
      setAnimationTick((tick) => {
        if (tick >= totalTicks - 1) {
          window.clearInterval(timer)
          return tick
        }
        return tick + 1
      })
    }, 520)
    return () => window.clearInterval(timer)
  }, [isOpen, flowStages.length])

  if (!isOpen) return null

  const decryptedMessage = message.content_decrypted || 'Message content unavailable'
  const data = {
    hasPlaintext: Boolean(message.content_decrypted),
    encryptionReady: message.encryption_version === 'AES-256-GCM',
    sessionReady,
    signatureStatus: securityStatus(message.signature_status),
    integrityStatus: securityStatus(message.integrity_status),
  }
  const activeStage = Math.min(Math.floor(animationTick / 3), flowStages.length - 1)
  const activePhase = animationTick % 3
  const completed = animationTick >= flowStages.length * 3 - 1

  const statusFor = (stage, index) => {
    const ready = stage.ready(data)
    if (!ready) return index <= activeStage ? 'Unavailable' : 'Pending'
    const hasInvalidVerification = (stage.key === 'sender-protection' && data.signatureStatus === 'invalid')
      || (stage.key === 'receiver-verification' && (data.signatureStatus === 'invalid' || data.integrityStatus === 'invalid'))
    if (hasInvalidVerification) {
      if (index < activeStage || completed) return 'Invalid'
      if (index === activeStage) return activePhase === 0 ? 'Processing' : 'Invalid'
    }
    if (index < activeStage || completed) return 'Complete'
    if (index > activeStage) return 'Pending'
    if (activePhase === 0) return 'Processing'
    if (activePhase === 1) return 'Verified'
    return 'Complete'
  }

  const activeMessage = flowStages[activeStage]
  const isPayloadStage = activeMessage.key === 'sender-payload'
  const isFinalStage = activeMessage.key === 'receiver-plaintext'
  const senderStatus = data.signatureStatus === 'verified' ? 'Verified' : data.signatureStatus === 'invalid' ? 'Invalid' : 'Unavailable'
  const receiverStatus = data.signatureStatus === 'verified' && data.integrityStatus === 'verified'
    ? 'Verified'
    : data.signatureStatus === 'invalid' || data.integrityStatus === 'invalid' ? 'Invalid' : 'Unavailable'

  return createPortal(
    <div
      className="security-flow-backdrop fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-slate-950/70 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-label="Message security flow"
      onClick={onClose}
    >
      <div
        className="security-flow-modal panel-enter flex w-[min(720px,calc(100vw-32px))] max-h-[calc(100vh-32px)] min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-surface-elevated shadow-popover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="relative overflow-hidden border-b border-border px-5 py-5 sm:px-7">
          <div className="security-flow-orbit" aria-hidden="true" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-accent">
                <ShieldCheckIcon className="h-4 w-4" /> Message security
              </div>
              <h2 className="text-xl font-semibold text-text-primary">Alice <span className="text-accent">→</span> Bob</h2>
              <p className="mt-1 max-w-lg text-sm text-text-muted">
                {isOutgoing ? 'Sender perspective: your message leaves Alice protected.' : 'Receiver perspective: Bob receives and opens the protected message.'}
              </p>
            </div>
            <button type="button" onClick={onClose} className="icon-btn" aria-label="Close security flow" title="Close security flow">
              <CloseIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="security-flow-content min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-5 py-5 sm:px-7">
          <div className="security-flow-transport mb-5">
            <div className={`security-flow-packet ${isPayloadStage ? 'is-hidden-payload' : ''} ${isFinalStage ? 'is-complete' : ''}`}>
              {isPayloadStage ? <LockIcon className="h-5 w-5" /> : <span className="security-flow-packet-text">{decryptedMessage}</span>}
            </div>
            <div className="security-flow-transport-label">
              <span>{activeMessage.label}</span>
              <span>{completed ? 'Complete' : statusFor(activeMessage, activeStage)}</span>
            </div>
          </div>
          <div className="security-flow-boundary" aria-label="Message sent and received boundary">
            <span>Alice · Sender</span><span className="security-flow-boundary-line" /><span>Message Sent</span>
            <span className="security-flow-boundary-arrow">→</span><span>Message Received · Bob</span>
          </div>
          <div className="security-flow-lanes">
            {[{ label: 'Alice · Sender', stages: SENDER_STAGES, offset: 0, signature: senderStatus }, { label: 'Bob · Receiver', stages: RECEIVER_STAGES, offset: SENDER_STAGES.length, signature: receiverStatus }].map((lane) => (
              <section key={lane.label} className="security-flow-lane">
                <div className="security-flow-lane-heading">
                  <span>{lane.label}</span>
                  <span className="security-flow-lane-status">{lane.signature}</span>
                </div>
                <div className="security-flow-timeline">
                  {lane.stages.map((stage, laneIndex) => {
                    const index = lane.offset + laneIndex
                    const status = statusFor(stage, index)
                    const active = status === 'Processing' || status === 'Verified'
                    const isFinal = stage.key === 'receiver-plaintext'
                    return (
                      <div key={stage.key} className={`security-flow-stage ${active ? 'is-active' : ''} ${status === 'Complete' ? 'is-complete' : ''} ${status === 'Unavailable' ? 'is-unavailable' : ''} ${isFinal ? 'is-final' : ''}`}>
                        <div className="security-flow-node" aria-hidden="true">
                          {status === 'Complete' || status === 'Verified' ? <ShieldCheckIcon className="h-4 w-4" /> : <span>{index + 1}</span>}
                        </div>
                        <div className="min-w-0 flex-1 rounded-xl border border-border/80 bg-surface px-3.5 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <h3 className="text-sm font-semibold text-text-primary">{stage.label}</h3>
                              <div className="mt-1 text-[9px] font-bold uppercase tracking-[0.16em] text-accent/80">{stage.algorithm}</div>
                              <p className="mt-1 text-xs leading-relaxed text-text-muted">{stage.detail}</p>
                            </div>
                            <span className={`sec-chip shrink-0 !px-2 !py-1 text-[10px] ${status === 'Complete' || status === 'Verified' ? 'good' : status === 'Invalid' ? 'danger' : 'warn'}`}>
                              {status}
                            </span>
                          </div>
                          {stage.key === 'sender-payload' && (
                            <div className="mt-3 flex items-center gap-2 rounded-lg border border-accent/20 bg-accent-soft px-3 py-2 text-xs text-text-secondary">
                              <LockIcon className="h-3.5 w-3.5 shrink-0 text-accent" />
                              Encrypted payload details are intentionally hidden.
                            </div>
                          )}
                          {isFinal && status === 'Complete' && (
                            <div className="mt-3 rounded-lg border border-success/25 bg-success/10 px-3 py-2.5 text-sm leading-relaxed text-text-primary">
                              {decryptedMessage}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border bg-surface/60 px-5 py-3 sm:px-7">
          <span className="text-[11px] text-text-muted">Private cryptographic material is never shown.</span>
          <button type="button" onClick={onClose} className="btn-secondary !px-3 !py-1.5 text-xs">Close</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default function MessageBubble({
  message,
  isOutgoing,
  sessionReady = false,
  onReply,
  onScrollToMessage,
  onEdit,
  onDelete,
  isEditing,
  onStartEdit,
  onCancelEdit,
  onReact,
  currentUserId,
  onOpenReactions,
  onOpenMore,
  onCloseMenu,
}) {
  const [editContent, setEditContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [editError, setEditError] = useState(null)
  const [showSecurityFlow, setShowSecurityFlow] = useState(false)
  const editInputRef = useRef(null)

  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  const editedTime = message.edited_at
    ? new Date(message.edited_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  // Determine if this message is hidden for the current user ("me" deletion).
  // Other participants (and "everyone" placeholders) are unaffected; the
  // deleted-for-everyone placeholder itself is handled later in the render.
  const isDeletedForMe =
    message.delete_type === 'me' && message.deleted_by === currentUserId

  const senderName = !isOutgoing && message.sender_name ? message.sender_name : ''

  // Initialize edit content when editing starts
  useEffect(() => {
    if (isEditing) {
      setEditContent(message.content_decrypted || message.content_encrypted || '')
      setEditError(null)
      setTimeout(() => editInputRef.current?.focus(), 0)
    }
  }, [isEditing, message.id, message.content_encrypted, message.content_decrypted])

  const handleReplyClick = () => {
    if (onReply) onReply(message)
  }

  const handleReplyPreviewClick = () => {
    if (onScrollToMessage && message.reply_preview) {
      onScrollToMessage(message.reply_preview.id)
    }
  }

  const handleStartEdit = () => {
    if (onCloseMenu) onCloseMenu()
    if (onStartEdit) onStartEdit(message)
  }

  const handleCancelEdit = () => {
    if (onCancelEdit) onCancelEdit(message)
  }

  const handleSaveEdit = async () => {
    const trimmed = editContent.trim()
    if (!trimmed || isSaving) return
    if (trimmed === message.content_encrypted) {
      handleCancelEdit()
      return
    }
    setIsSaving(true)
    setEditError(null)
    try {
      await onEdit(message, trimmed)
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

  const handleToggleReaction = (emoji) => {
    if (onReact) onReact(message, emoji)
  }

  // If the message is deleted for everyone, show placeholder
  if (message.is_deleted && message.delete_type === 'everyone') {
    return (
      <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}>
        <div className={`relative max-w-[70%] rounded-2xl px-3 py-2 text-sm shadow-card ${isOutgoing ? 'bubble-out opacity-70' : 'bubble-in opacity-70'
          }`}>
          <div className="italic opacity-80">This message was deleted.</div>
          <div className="mt-1 text-[10px] opacity-70">{time}</div>
        </div>
      </div>
    )
  }

  // If deleted for me only, hide entirely (the requesting user doesn't see it)
  if (isDeletedForMe && message.delete_type === 'me') {
    return null
  }

  return (
    <div
      className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} group relative`}
      onContextMenu={(event) => {
        event.preventDefault()
        if (onOpenMore) onOpenMore(message, null, { x: event.clientX, y: event.clientY })
      }}
    >
      <div className={`relative max-w-[75%] sm:max-w-[70%] message-enter ${isOutgoing ? 'bubble-out rounded-2xl rounded-br-md' : 'bubble-in rounded-2xl rounded-bl-md'
        } px-3.5 py-2.5 text-sm`}>
        <SenderName name={senderName} isOutgoing={isOutgoing} />

        {/* Reply preview indicator */}
        {message.reply_preview && (
          <button
            onClick={handleReplyPreviewClick}
            className={`block w-full text-left mb-1.5 rounded-lg px-2 py-1 text-xs border-l-2 ${isOutgoing
              ? 'bg-white/10 border-white/50 text-white/80 hover:bg-white/20'
              : 'bg-surface-hover border-accent text-text-muted hover:bg-surface-active'
              }`}
            title="Click to view original message"
          >
            <span className="font-semibold block truncate">
              {message.reply_preview.is_deleted ? 'Deleted message' : 'Reply'}
            </span>
            <span className="block truncate opacity-80">
              {message.reply_preview.content_decrypted || message.reply_preview.content_encrypted && '🔒 Encrypted'}
            </span>
          </button>
        )}

        {message.message_type !== 'text' && (
          <TypeChip messageType={message.message_type} isOutgoing={isOutgoing} />
        )}

        {isEditing ? (
          <div>
            <textarea
              ref={editInputRef}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              onKeyDown={handleEditKeyDown}
              className={`input-base w-full resize-none text-sm ${isOutgoing ? 'bg-white/10 text-white placeholder-white/50' : 'bg-surface-elevated text-text-primary'
                }`}
              rows={2}
              disabled={isSaving}
              aria-label="Edit message"
            />
            {editError && <div className="text-xs text-danger mt-1">{editError}</div>}
            <div className="flex items-center gap-2 text-xs mt-1.5">
              <button
                onClick={handleSaveEdit}
                disabled={!editContent.trim() || isSaving}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${isOutgoing
                  ? 'bg-white/20 text-white hover:bg-white/30 disabled:opacity-50'
                  : 'bg-accent text-white hover:bg-accent-hover disabled:opacity-50'
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
                className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${isOutgoing ? 'text-white/70 hover:text-white' : 'text-text-muted hover:text-text-primary'
                  }`}
                aria-label="Cancel edit"
              >
                Cancel
              </button>
              <span className={`text-[10px] hidden sm:inline ${isOutgoing ? 'text-white/50' : 'text-text-muted'}`}>
                Enter to save · Esc to cancel
              </span>
            </div>
          </div>
        ) : (
          <>
            <div className="break-words whitespace-pre-wrap">{message.content_decrypted || message.content_encrypted}</div>
            {message.attachments?.length > 0 && (
              <div className="mt-2 space-y-2">
                {message.attachments.map((attachment) => (
                  <div key={attachment.id} className="rounded-xl border border-border/60 overflow-hidden">
                    {attachment.local_url && attachment.mime_type?.startsWith('image/') ? (
                      <img
                        src={attachment.local_url}
                        alt={attachment.original_filename}
                        className="max-h-64 max-w-full rounded object-contain"
                      />
                    ) : attachment.local_url && attachment.mime_type?.startsWith('audio/') ? (
                      <audio controls preload="metadata" className="max-w-full px-2 py-1" aria-label="Voice message">
                        <source src={attachment.local_url} type={attachment.mime_type} />
                        Your browser cannot play this voice message.
                      </audio>
                    ) : (
                      <span className="flex items-center gap-2 px-2 py-1.5 text-xs">
                        <FileIcon className="w-3.5 h-3.5 text-text-muted" />
                        {attachment.original_filename}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className={`flex items-center gap-1.5 mt-1 text-[10px] ${isOutgoing ? 'text-white/70' : 'text-text-muted'}`}>
              <span>{time}</span>
              {message.is_edited && (
                <span title={editedTime ? `Edited at ${editedTime}` : 'Edited'}>· Edited</span>
              )}
              {message.signature_status === 'verified' && (
                <span className="inline-flex items-center gap-0.5" title="Digital signature verified">
                  <ShieldCheckIcon className="w-3 h-3" /> Verified
                </span>
              )}
              <button
                type="button"
                onClick={() => setShowSecurityFlow(true)}
                className="inline-flex items-center gap-0.5 rounded px-1 py-0.5 transition-colors hover:bg-white/10 hover:text-white"
                title="View message security flow"
                aria-label="View message security flow"
              >
                <ShieldCheckIcon className="w-3 h-3" />
              </button>
              {message.signature_status === 'failed' && (
                <span title="Message verification failed" className="text-danger">· Verification Failed</span>
              )}
              {isOutgoing && (
                <span className="inline-flex items-center" title="Delivered">
                  <CheckIcon className="w-3.5 h-3.5" />
                </span>
              )}
            </div>
          </>
        )}

        {/* Hover actions: react, reply, forward, edit, more */}
        {!isEditing && (
          <div className="hidden group-hover:flex absolute -top-3.5 right-0 glass rounded-xl shadow-popover px-1 py-1 gap-0.5 toolbar-enter z-10">
            <ActionButton label="React" onClick={(event) => onOpenReactions(message, event.currentTarget, undefined)}>🙂</ActionButton>
            <ActionButton label="Reply" onClick={handleReplyClick}>
              <ReplyIcon className="w-4 h-4" />
            </ActionButton>
            <ActionButton label="Forward" disabled title="Forwarding coming soon">
              <ForwardIcon className="w-4 h-4" />
            </ActionButton>
            {isOutgoing && message.message_type !== 'system' && (
              <ActionButton label="Edit message" onClick={handleStartEdit}>
                <EditIcon className="w-4 h-4" />
              </ActionButton>
            )}
            <ActionButton label="More" onClick={(event) => onOpenMore(message, event.currentTarget, undefined)}>
              <MoreIcon className="w-4 h-4" />
            </ActionButton>
          </div>
        )}

        {message.reactions?.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {message.reactions.map((reaction) => (
              <button
                key={reaction.emoji}
                onClick={() => handleToggleReaction(reaction.emoji)}
                className={`rounded-full border px-2 py-0.5 text-[11px] transition-colors ${reaction.reacted_by_me ? 'border-accent bg-accent-soft' : 'border-border bg-surface-elevated hover:bg-surface-hover'
                  }`}
                title={`Reacted by ${reaction.users?.slice(0, 2).map((u) => u.name).join(', ')}${reaction.count > 2 ? ` and ${reaction.count - 2} others` : ''
                  }`}
              >
                {reaction.emoji} {reaction.count}
              </button>
            ))}
          </div>
        )}

        <SecurityFlowModal
          isOpen={showSecurityFlow}
          onClose={() => setShowSecurityFlow(false)}
          message={message}
          sessionReady={sessionReady}
          isOutgoing={isOutgoing}
        />
      </div>
    </div>
  )
}