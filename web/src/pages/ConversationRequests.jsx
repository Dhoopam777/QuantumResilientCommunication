import { useCallback, useEffect, useState } from 'react'
import { conversationRequestApi, userApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import ChatLayout from '../components/chat/ChatLayout'
import ConversationList from '../components/chat/ConversationList'
import Avatar from '../components/common/Avatar'
import EmptyState from '../components/common/EmptyState'
import Badge from '../components/common/Badge'
import { InboxIcon, UserPlusIcon, CheckIcon, CloseIcon, SendIcon, SearchIcon } from '../components/icons'

function RequestCard({ request, incoming, onAction }) {
  const person = incoming ? request.sender : request.receiver
  const statusClass = incoming
    ? request.status === 'PENDING' ? 'bg-warning/10 text-warning' : 'bg-accent-soft text-accent'
    : 'bg-surface-hover text-text-muted'
  const statusText = incoming && request.status === 'PENDING'
    ? 'Pending'
    : request.status
  const statusLabel = incoming && request.status === 'PENDING'
    ? <span className="text-[10px] uppercase tracking-wider text-warning bg-warning/10 px-2 py-0.5 rounded-full">Pending</span>
    : <span className="text-[10px] uppercase tracking-wider text-text-muted bg-surface-hover px-2 py-0.5 rounded-full">{statusText}</span>

  return (
    <div className="card card-hover flex items-center justify-between gap-3 px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <Avatar name={person.display_name || person.username} src={person.profile_picture_url} size="md" online={person.status === 'online'} />
        <div className="min-w-0">
          <div className="font-medium text-text-primary truncate">{person.display_name || person.username}</div>
          <div className="text-xs text-text-muted truncate">@{person.username} · {person.status}</div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {statusLabel}
        {incoming ? (
          <>
            <button className="btn-primary !px-2.5 !py-1.5 text-xs" onClick={() => onAction(request.id, 'accept')}>
              <CheckIcon className="w-3.5 h-3.5" /> Accept
            </button>
            <button className="btn-secondary !px-2.5 !py-1.5 text-xs" onClick={() => onAction(request.id, 'decline')}>
              <CloseIcon className="w-3.5 h-3.5" /> Decline
            </button>
          </>
        ) : (
          <>
            {request.status === 'PENDING' && (
              <button className="btn-ghost !px-2.5 !py-1.5 text-xs" onClick={() => onAction(request.id, 'cancel')}>
                <span className="align-middle">Cancel</span>
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function ConversationRequests() {
  const { user, logout } = useAuth()
  const [incoming, setIncoming] = useState([])
  const [outgoing, setOutgoing] = useState([])
  const [username, setUsername] = useState('')
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [error, setError] = useState('')
  const [tab, setTab] = useState('incoming')

  const load = useCallback(async () => {
    const [incomingResponse, outgoingResponse] = await Promise.all([
      conversationRequestApi.incoming(),
      conversationRequestApi.outgoing(),
    ])
    if (incomingResponse.status === 200) setIncoming(incomingResponse.data)
    if (outgoingResponse.status === 200) setOutgoing(outgoingResponse.data)
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    (async () => {
      const { WebSocketClient } = await import('../lib/websocket')
      const ws = new WebSocketClient()
      ws.on('conversation_request_received', load)
      ws.on('conversation_request_accepted', load)
      ws.on('conversation_request_declined', load)
      ws.on('conversation_request_cancelled', load)
      ws.on('conversation_created', () => window.dispatchEvent(new Event('conversation-created')))
      return () => ws.disconnect()
    })()
  }, [load])

  const send = useCallback(async (usernameToSend) => {
    const res = await conversationRequestApi.create(usernameToSend)
    if (res.status !== 201) {
      setError(res.error || 'Unable to send request.')
    }
    setUsername('')
    setSearchResults([])
    load()
  }, [load])

  useEffect(() => {
    if (username.trim().length < 2) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(async () => {
      const response = await userApi.search(username.trim())
      setSearchResults(response.status === 200 && Array.isArray(response.data) ? response.data : [])
    }, 250)
    return () => clearTimeout(timer)
  }, [username])

  return (
    <ChatLayout
      user={user}
      onLogout={logout}
      search={setSearch}
      onSearchChange={setSearch}
      sidebarContent={null}
    >
      <div className="flex-1 flex flex-col min-h-0">
        <div className="border-b border-border bg-surface/50 px-4 py-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
            Requests
            <span className="ml-1.5 inline-flex rounded-full bg-surface-hover px-1.5 py-0.5 text-[9px] font-semibold text-text-secondary normal-case tracking-normal">Total: {incoming.length + outgoing.length}</span>
          </h2>
        </div>

        <div className="p-4 space-y-4">
          {/* Search and send section */}
          <div>
            <span className="text-xs text-text-secondary block mb-1">Send request</span>
            <div className="flex items-center gap-2">
              <input
                className="input flex-1"
                placeholder="Search username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                aria-label="Search username"
              />
              <button
                type="button"
                onClick={() => username.trim() && send(username.trim())}
                className="btn-primary"
                title="Send request"
                aria-label="Send request"
              >
                <SendIcon className="w-4 h-4" />
              </button>
            </div>
            {username.trim().length > 0 && searchResults.length > 0 && (
              <div className="mt-2 rounded-xl border border-border divide-y divide-border overflow-hidden">
                {searchResults.map((person) => (
                  <button key={person.username} onClick={() => send(person.username)} className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-surface-hover transition-colors">
                    <Avatar name={person.display_name || person.username} src={person.profile_picture_url} size="sm" online={person.status === 'online'} />
                    <span className="font-medium text-sm">@{person.username}</span>
                    <span className="ml-auto text-xs text-text-muted">{person.display_name || ''}</span>
                  </button>
                ))}
              </div>
            )}
            {error && <div className="mt-2 text-sm text-danger" role="alert">{error}</div>}
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 mb-4">
            <button
              type="button"
              className={`tab-btn ${tab === 'incoming' ? 'active' : ''}`}
              onClick={() => setTab('incoming')}
            >
              <InboxIcon className="w-4 h-4 inline mr-1.5 align-[-2px]" /> Incoming
              {incoming.length > 0 && (
                <span className="ml-1.5 inline-flex rounded-full bg-accent-soft text-accent px-1.5 py-0.5 text-[10px] font-bold">{incoming.length}</span>
              )}
            </button>
            <button
              type="button"
              className={`tab-btn ${tab === 'outgoing' ? 'active' : ''}`}
              onClick={() => setTab('outgoing')}
            >
              <UserPlusIcon className="w-4 h-4 inline mr-1.5 align-[-2px]" /> Outgoing
              {outgoing.length > 0 && (
                <span className="ml-1.5 inline-flex rounded-full bg-accent-soft text-accent px-1.5 py-0.5 text-[10px] font-bold">{outgoing.length}</span>
              )}
            </button>
          </div>

          {/* Cards */}
          <div className="p-4 bg-surface rounded-xl space-y-2">
            {tab === 'incoming' ? (
              <div className="space-y-2">
                {incoming.length === 0 ? (
                  <EmptyState
                    icon={<InboxIcon className="w-8 h-8 text-accent" />}
                    title="No pending incoming requests"
                    description="Requests from other users will appear here. Use the search box above to reach out first."
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-2">
                    {incoming.map((request) => <RequestCard key={request.id} request={request} incoming onAction={action} />)}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {outgoing.length === 0 ? (
                  <EmptyState
                    icon={<UserPlusIcon className="w-8 h-8 text-accent" />}
                    title="No outgoing requests"
                    description="Search for a username above to send a conversation request."
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-2">
                    {outgoing.map((request) => <RequestCard key={request.id} request={request} onAction={action} />)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </ChatLayout>
  )
}