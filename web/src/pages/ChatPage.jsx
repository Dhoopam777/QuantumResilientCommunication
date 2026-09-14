import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ChatHeader from '../components/chat/ChatHeader'
import ChatLayout from '../components/chat/ChatLayout'
import ConversationList from '../components/chat/ConversationList'
import DetailsPanel from '../components/chat/DetailsPanel'
import MessageComposer from '../components/chat/MessageComposer'
import MessageList from '../components/chat/MessageList'
import SecurityStatus from '../components/chat/SecurityStatus'
import UserSearch from '../components/chat/UserSearch'
import EmptyState from '../components/common/EmptyState'
import { useAuth } from '../context/AuthContext'
import { useChat } from '../context/ChatContext'
import {
  attachmentApi,
  conversationApi,
  cryptoApi,
  getAccessToken,
  groupApi,
  messageApi,
} from '../lib/api'
import {
  decryptBytes,
  decryptMessage,
  encryptBytes,
  encryptMessage,
  ensureDeviceIdentity,
  establishClientSession,
  restoreSession,
  signMessage,
} from '../lib/pqc'
import { WebSocketClient } from '../lib/websocket'

export default function ChatPage() {
  const { activeConversationId: conversationId, showDetails } = useChat()
  const navigate = useNavigate()
  const { isLoggedIn, user, accessToken, logout, registerWebSocket, unregisterWebSocket } = useAuth()
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [wsMessages, setWsMessages] = useState([])
  const [search, setSearch] = useState('')
  const [findUsersOpen, setFindUsersOpen] = useState(false)
  const [replyTo, setReplyTo] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const wsClientRef = useRef(null)
  const seenMessageIdsRef = useRef(new Set())
  const wsTokenRef = useRef('')
  const sessionKeyRef = useRef(null)

  const decryptMessagePayload = useCallback(async (message) => {
    if (!message.nonce || !message.authentication_tag || !sessionKeyRef.current) return message
    try {
      const content = await decryptMessage(
        sessionKeyRef.current,
        message.content_encrypted,
        message.nonce,
        message.authentication_tag,
      )
      const attachments = await Promise.all((message.attachments || []).map(async (attachment) => {
        if (!attachment.encryption_algorithm) return attachment
        const response = await attachmentApi.download(attachment.id)
        if (response.status !== 200 || !response.blob) throw new Error('Attachment download failed')
        const encryptedBytes = new Uint8Array(await response.blob.arrayBuffer())
        const plaintext = await decryptBytes(
          sessionKeyRef.current,
          encryptedBytes,
          attachment.nonce,
          attachment.authentication_tag,
        )
        return {
          ...attachment,
          local_url: URL.createObjectURL(new Blob([plaintext], { type: attachment.mime_type })),
        }
      }))
      return { ...message, content_encrypted: content, content_decrypted: content, attachments }
    } catch {
      return { ...message, content_decrypted: 'Unable to decrypt message.', attachments: [] }
    }
  }, [])

  const fetchConversation = useCallback(async () => {
    if (!conversationId) return
    const res = await conversationApi.get(conversationId)
    if (res.status === 200) {
      setConversation(res.data)
    }
  }, [conversationId])

  const fetchMessages = useCallback(async () => {
    if (!conversationId) return
    const res = await messageApi.list(conversationId)
    if (res.status === 200 && Array.isArray(res.data)) {
      const decrypted = await Promise.all(res.data.map(decryptMessagePayload))
      setMessages(decrypted)
      res.data.forEach((m) => {
        if (m.id) seenMessageIdsRef.current.add(m.id)
      })
    }
  }, [conversationId, decryptMessagePayload])

  useEffect(() => {
    if (isLoggedIn) {
      ensureDeviceIdentity().catch(() => {
        console.error('Device key migration failed')
      })
    }
  }, [isLoggedIn])

  const ensureSession = useCallback(async () => {
    if (sessionKeyRef.current || !conversation?.participants?.length) return sessionKeyRef.current
    const peer = conversation.participants.find((participant) => participant.user_id !== user?.id)
    if (!peer) return null
    const sessions = await cryptoApi.sessions()
    const existing = sessions.status === 200
      ? sessions.data.find((session) => session.conversation_id === conversationId && session.status === 'active')
      : null
    sessionKeyRef.current = existing
      ? await restoreSession(existing)
      : await establishClientSession(peer.username)
    return sessionKeyRef.current
  }, [conversation, conversationId, user?.id])

  // The selected conversation lives in ChatContext (not the URL); ChatProvider
  // persists it for restore after refresh. Reset all per-conversation state
  // (including the session key and seen-message set) when switching chats so
  // the new conversation is fetched, joined and decrypted cleanly.
  useEffect(() => {
    setConversation(null)
    setMessages([])
    setWsMessages([])
    setReplyTo(null)
    setEditingId(null)
    sessionKeyRef.current = null
    seenMessageIdsRef.current = new Set()
  }, [conversationId])

  // Set up WebSocket connection for real-time messaging
  useEffect(() => {
    if (!isLoggedIn || !conversationId) return

    const token = accessToken || getAccessToken()
    if (!token) return

    const wsClient = new WebSocketClient()
    wsClientRef.current = wsClient
    wsTokenRef.current = token
    registerWebSocket(wsClient)

    wsClient.on('new_message', (data) => {
      const msg = data.message
      if (!msg || !msg.id) return
      if (!seenMessageIdsRef.current.has(msg.id)) {
        seenMessageIdsRef.current.add(msg.id)
        if (msg.nonce && msg.authentication_tag && sessionKeyRef.current) {
          decryptMessagePayload(msg)
            .then((decrypted) => setWsMessages((prev) => [...prev, decrypted]))
        } else {
          setWsMessages((prev) => [...prev, msg])
        }
      }
    })

    wsClient.on('message_edited', (data) => {
      const msg = data.message
      if (!msg || !msg.id) return
      // Update the message in-place in the REST-fetched messages
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, ...msg } : m))
      )
      // Also update in wsMessages if present
      setWsMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, ...msg } : m))
      )
      // If this message is currently being edited, close the edit mode
      setEditingId((current) => (current === msg.id ? null : current))
    })

    wsClient.on('message_deleted', (data) => {
      const msg = data.message
      if (!msg || !msg.id) return
      // Update the message in-place in both REST-fetched and WS-received messages
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, ...msg } : m))
      )
      setWsMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, ...msg } : m))
      )
    })

    const handleReactionEvent = (data) => {
      if (!data.message_id || !Array.isArray(data.reactions)) return
      const reactions = data.reactions.map((reaction) => ({
        ...reaction,
        reacted_by_me: reaction.users?.some((reactionUser) => reactionUser.id === user?.id) || false,
      }))
      const update = (prev) => prev.map((m) => (
        m.id === data.message_id ? { ...m, reactions } : m
      ))
      setMessages(update)
      setWsMessages(update)
    }
    wsClient.on('reaction_added', handleReactionEvent)
    wsClient.on('reaction_removed', handleReactionEvent)

    const refreshConversations = () => window.dispatchEvent(new Event('conversation-created'))
    wsClient.on('group_created', refreshConversations)
    wsClient.on('member_added', (data) => {
      if (data.conversation?.id === conversationId) setConversation(data.conversation)
      refreshConversations()
    })
    wsClient.on('member_removed', (data) => {
      if (data.conversation_id === conversationId && data.username === user?.username) {
        navigate('/test/chat')
      }
      refreshConversations()
    })
    wsClient.on('group_updated', (data) => {
      if (data.conversation?.id === conversationId) setConversation(data.conversation)
      refreshConversations()
    })

    wsClient.on('auth_success', () => {
      setWsStatus('connected')
      wsClient.joinConversation(conversationId)
    })

    wsClient.on('auth_error', () => {
      setWsStatus('auth_failed')
    })

    wsClient.on('connection_close', () => {
      setWsStatus('disconnected')
    })

    wsClient.on('connection_open', () => {
      setWsStatus('connecting')
    })

    wsClient.setAuthFailureCallback(() => {
      setWsStatus('auth_failed')
    })

    wsClient.connect(token)

    return () => {
      wsClient.disconnect()
      wsClientRef.current = null
      unregisterWebSocket()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, conversationId, registerWebSocket, unregisterWebSocket])

  // Reconnect WebSocket when the access token changes (token refresh)
  useEffect(() => {
    const wsClient = wsClientRef.current
    const token = accessToken || getAccessToken()
    if (wsClient && token && token !== wsTokenRef.current) {
      wsTokenRef.current = token
      wsClient.reconnectWithToken(token)
    }
  }, [accessToken])

  // Fetch conversation and messages on mount.
  //
  // IMPORTANT: this effect must NOT list `ensureSession` (or any callback that
  // closes over `conversation`) in its dependency array. `ensureSession`'s
  // identity changes whenever `conversation` changes, and this effect calls
  // `fetchConversation()` which sets `conversation` — listing it would create an
  // infinite fetch/re-render loop that orphans the open message menu and breaks
  // message actions. We call the latest callbacks directly; their own
  // useCallback deps keep them semantically fresh.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (isLoggedIn && conversationId) {
      fetchConversation()
      ensureSession().finally(fetchMessages)
    }
  }, [isLoggedIn, conversationId])

  const handleReply = (message) => {
    setReplyTo(message)
  }

  const handleCancelReply = () => {
    setReplyTo(null)
  }

  const handleStartEdit = (message) => {
    setEditingId(message.id)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
  }

  const handleEditMessage = async (message, newContent) => {
    if (!message || !message.id) return
    const key = await ensureSession()
    if (!key) throw new Error('Secure session unavailable')
    const encrypted = await encryptMessage(key, newContent)
    const signature_created_at = new Date().toISOString().replace('Z', '+00:00')
    const payload = {
      content_encrypted: encrypted.ciphertext,
      content_hash: encrypted.ciphertext,
      encryption_version: 'AES-256-GCM',
      nonce: encrypted.nonce,
      authentication_tag: encrypted.tag,
      signature: await signMessage({
        conversation_id: message.conversation_id,
        sender_id: user.id,
        message_type: message.message_type,
        content_encrypted: encrypted.ciphertext,
        attachments: [],
        timestamp: signature_created_at,
      }),
      signature_created_at,
    }
    const res = await messageApi.edit(message.id, payload)
    if (res.status === 200 && res.data) {
      // Update the message in-place locally
      setMessages((prev) =>
        prev.map((m) => (m.id === res.data.id ? { ...m, ...res.data } : m))
      )
      setWsMessages((prev) =>
        prev.map((m) => (m.id === res.data.id ? { ...m, ...res.data } : m))
      )
      setEditingId(null)
    } else {
      const err = new Error(res.data?.detail || 'Failed to edit message')
      throw err
    }
  }

  const handleDeleteMessage = async (message, mode) => {
    if (!message || !message.id) return
    const res = await messageApi.delete(message.id, mode)
    if (res.status === 200 && res.data) {
      // The WebSocket broadcast will handle the UI update,
      // but also update local state in case the sender doesn't
      // receive their own broadcast (some setups exclude sender).
      setMessages((prev) =>
        prev.map((m) => (m.id === res.data.id ? { ...m, ...res.data } : m))
      )
      setWsMessages((prev) =>
        prev.map((m) => (m.id === res.data.id ? { ...m, ...res.data } : m))
      )
    } else {
      const err = new Error(res.data?.detail || 'Failed to delete message')
      throw err
    }

  }

  const handleReact = async (message, emoji) => {
    const res = await messageApi.toggleReaction(message.id, emoji)
    if (res.status === 200 && res.data) {
      const update = (prev) => prev.map((m) => (m.id === message.id ? { ...m, ...res.data } : m))
      setMessages(update)
      setWsMessages(update)
    } else {
      throw new Error(res.data?.detail || 'Failed to update reaction')
    }
  }

  const handleAddGroupMember = async (username) => {
    if (!conversation?.is_group) return
    const res = await groupApi.addMember(conversation.id, username)
    if (res.status === 200 && res.data) {
      setConversation(res.data)
      return
    }
    throw new Error(res.data?.detail || 'Failed to add group member')
  }

  const handleRemoveGroupMember = async (username) => {
    if (!conversation?.is_group) return
    const res = await groupApi.removeMember(conversation.id, username)
    if (res.status === 200 && res.data) {
      setConversation(res.data)
      return
    }
    throw new Error(res.data?.detail || 'Failed to remove group member')
  }

  const validateAttachment = async (file) => {
    const allowed = {
      'image/png': '.png',
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/webp': '.webp',
      'audio/webm': '.webm',
    }
    const expectedExtension = allowed[file.type]
    const extension = `.${file.name.split('.').pop().toLowerCase()}`
    if (!expectedExtension || (!Array.isArray(expectedExtension)
      ? extension !== expectedExtension
      : !expectedExtension.includes(extension))) {
      throw new Error('Only PNG, JPEG, WebP, and recorded WebM audio are supported')
    }
    if (file.size <= 0 || file.size + 16 > 10 * 1024 * 1024) {
      throw new Error('Attachment exceeds the maximum encrypted size')
    }
    if (!file.type.startsWith('image/')) return
    const objectUrl = URL.createObjectURL(file)
    try {
      await new Promise((resolve, reject) => {
        const image = new Image()
        image.onload = resolve
        image.onerror = () => reject(new Error('Image could not be decoded'))
        image.src = objectUrl
      })
    } finally {
      URL.revokeObjectURL(objectUrl)
    }
  }

  const uploadEncryptedAttachments = async (files, key, conversationId) => {
    const uploaded = []
    for (const file of files) {
      await validateAttachment(file)
      const encrypted = await encryptBytes(key, new Uint8Array(await file.arrayBuffer()))
      const formData = new FormData()
      formData.append('conversation_id', conversationId)
      formData.append('file', new File([encrypted.ciphertext], file.name, { type: 'application/octet-stream' }))
      formData.append('encryption_algorithm', 'AES-256-GCM')
      formData.append('declared_mime_type', file.type)
      formData.append('nonce', encrypted.nonce)
      formData.append('authentication_tag', encrypted.tag)
      const response = await attachmentApi.upload(formData)
      if (response.status !== 201) throw new Error(response.data?.detail || 'Attachment upload failed')
      uploaded.push(response.data)
    }
    return uploaded
  }

  const handleSend = async (content, replyTarget = null, files = [], messageType = 'text') => {
    if (!conversationId || (!content.trim() && files.length === 0)) return
    const key = await ensureSession()
    if (!key) throw new Error('Secure session unavailable')
    const uploadedAttachments = await uploadEncryptedAttachments(files, key, conversationId)
    try {
      const messageContent = content.trim() || (messageType === 'audio' ? 'Voice message' : 'Attachment')
      const encrypted = await encryptMessage(key, messageContent)
      const signature_created_at = new Date().toISOString().replace('Z', '+00:00')
      // Sign attachments in id order — the canonical order the backend verifier
      // uses when reconstructing the signed payload.
      const signedAttachments = [...uploadedAttachments].sort((a, b) => String(a.id).localeCompare(String(b.id)))
      const signature = await signMessage({
        conversation_id: conversationId,
        sender_id: user.id,
        message_type: messageType,
        content_encrypted: encrypted.ciphertext,
        attachments: signedAttachments.map((attachment) => ({
          id: attachment.id,
          original_filename: attachment.original_filename,
          mime_type: attachment.mime_type,
          file_size: attachment.file_size,
          checksum_sha256: attachment.checksum_sha256,
          width: attachment.width,
          height: attachment.height,
          encryption_algorithm: attachment.encryption_algorithm,
          nonce: attachment.nonce,
          authentication_tag: attachment.authentication_tag,
          encrypted_size: attachment.encrypted_size,
        })),
        timestamp: signature_created_at,
      })
      const payload = {
        conversation_id: conversationId,
        content_encrypted: encrypted.ciphertext,
        content_hash: encrypted.ciphertext,
        encryption_version: 'AES-256-GCM',
        nonce: encrypted.nonce,
        authentication_tag: encrypted.tag,
        signature,
        signature_created_at,
        message_type: messageType,
        reply_to: replyTarget ? replyTarget.id : null,
        reply_to_message_id: replyTarget ? replyTarget.id : null,
        attachment_ids: uploadedAttachments.map((attachment) => attachment.id),
      }
      const res = await messageApi.send(payload)
      if (res.status !== 201) throw new Error(res.data?.detail || 'Unable to send message')
      // WebSocket broadcast is the single source of truth for new messages
      setReplyTo(null)
    } catch (error) {
      await Promise.all(uploadedAttachments.map(async (attachment) => {
        const cleanup = await attachmentApi.delete(attachment.id)
        if (cleanup.status >= 300) throw new Error('Message failed and attachment cleanup failed')
      }))
      throw error
    }
  }

  // Merge REST-fetched and WebSocket-received messages into one chronological
  // list. Dedupe by id (WebSocket copies are freshest) and order strictly by
  // created_at so live-delivered messages keep their original position even
  // when they arrived via WebSocket after an older REST snapshot.
  //
  // IMPORTANT: this hook must be called unconditionally, BEFORE any early
  // return (Rules of Hooks). The login check below is a render branch only.
  const allMessages = useMemo(() => {
    const byId = new Map()
    for (const message of messages) {
      if (message && message.id) byId.set(message.id, message)
    }
    for (const message of wsMessages) {
      if (message && message.id) byId.set(message.id, message)
    }
    return Array.from(byId.values()).sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
      return aTime - bTime || String(a.id).localeCompare(String(b.id))
    })
  }, [messages, wsMessages])

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  return (
    <ChatLayout
      user={user}
      onLogout={logout}
      search={search}
      onSearchChange={setSearch}
      sidebarContent={
        <>
          <div className="px-4 pt-3 pb-2 border-b border-border">
            <button
              type="button"
              onClick={() => setFindUsersOpen((open) => !open)}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-hover"
              aria-expanded={findUsersOpen}
            >
              🔍 Search users
            </button>
          </div>
          {findUsersOpen && <UserSearch onClose={() => setFindUsersOpen(false)} />}
          <ConversationList activeConversationId={conversationId} search={search} />
        </>
      }
      showDetails={showDetails}
      detailsPanel={
        <DetailsPanel
          conversation={conversation}
          currentUserId={user?.id}
          canManage={conversation?.is_group && conversation.created_by === user?.id}
          onAddMember={handleAddGroupMember}
          onRemoveMember={handleRemoveGroupMember}
        />
      }
    >
      {conversationId ? (
        <>
          <ChatHeader conversation={conversation} currentUserId={user?.id} />
          <SecurityStatus
            user={user}
            authenticated={Boolean(accessToken)}
            sessionReady={Boolean(sessionKeyRef.current)}
            messages={allMessages}
          />
          <MessageList
            messages={allMessages}
            currentUserId={user?.id}
            sessionReady={Boolean(sessionKeyRef.current)}
            onReply={handleReply}
            onEdit={handleEditMessage}
            onDelete={handleDeleteMessage}
            editingId={editingId}
            onStartEdit={handleStartEdit}
            onCancelEdit={handleCancelEdit}
            onReact={handleReact}
          />
          <MessageComposer
            onSend={handleSend}
            disabled={!conversation}
            replyTo={replyTo}
            onCancelReply={handleCancelReply}
          />
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center">
          <EmptyState
            icon="💬"
            title="Welcome to QRC Chat"
            description="Select a conversation from the sidebar to start chatting, or create a new one."
          />
          <Link to="/test/conversations/new" className="btn-primary mt-2">
            New Conversation
          </Link>
        </div>
      )}
    </ChatLayout>
  )
}
