import { useCallback, useEffect, useState } from 'react'
import { conversationRequestApi, userApi, getAccessToken } from '../lib/api'
import { WebSocketClient } from '../lib/websocket'
import { useAuth } from '../context/AuthContext'
import ChatLayout from '../components/chat/ChatLayout'
import SidebarNav from '../components/sidebar/SidebarNav'
import ConversationList from '../components/chat/ConversationList'

function RequestCard({ request, incoming, onAction }) {
  const person = incoming ? request.sender : request.receiver
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
      <div className="min-w-0">
        <div className="font-medium text-text-primary truncate">{person.display_name || person.username}</div>
        <div className="text-xs text-text-muted">@{person.username} · {person.status}</div>
      </div>
      <div className="flex gap-2 shrink-0">
        {incoming ? (
          <>
            <button className="btn-primary text-xs" onClick={() => onAction(request.id, 'accept')}>Accept</button>
            <button className="btn-secondary text-xs" onClick={() => onAction(request.id, 'decline')}>Decline</button>
          </>
        ) : (
          <>
            <span className="text-xs text-text-muted self-center">{request.status}</span>
            {request.status === 'PENDING' && (
              <button className="btn-secondary text-xs" onClick={() => onAction(request.id, 'cancel')}>Cancel</button>
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
  const [searchResults, setSearchResults] = useState([])
  const [error, setError] = useState('')

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
    const ws = new WebSocketClient()
    ws.on('conversation_request_received', load)
    ws.on('conversation_request_accepted', load)
    ws.on('conversation_request_declined', load)
    ws.on('conversation_request_cancelled', load)
    ws.on('conversation_created', () => window.dispatchEvent(new Event('conversation-created')))
    ws.connect(getAccessToken())
    return () => ws.disconnect()
  }, [load])

  const search = async (value) => {
    setUsername(value)
    if (!value) return setSearchResults([])
    const response = await userApi.search(value)
    setSearchResults(response.status === 200 ? response.data : [])
  }

  const send = async (name) => {
    const response = await conversationRequestApi.create(name)
    if (response.status === 201) {
      setUsername('')
      setSearchResults([])
      load()
    } else {
      setError(response.data?.detail || 'Unable to send request')
    }
  }

  const action = async (id, type) => {
    const response = type === 'accept'
      ? await conversationRequestApi.accept(id)
      : type === 'decline'
        ? await conversationRequestApi.decline(id)
        : await conversationRequestApi.cancel(id)
    if (response.status >= 300) setError(response.data?.detail || 'Unable to update request')
    await load()
  }

  return (
    <ChatLayout
      user={user}
      onLogout={logout}
      sidebarContent={<><SidebarNav /><ConversationList /></>}
      showSidebar
    >
      <div className="flex-1 overflow-y-auto max-w-2xl mx-auto w-full">
        <div className="border-b border-border px-4 py-4">
          <h1 className="text-lg font-semibold text-text-primary">Conversation Requests</h1>
          <input
            value={username}
            onChange={(event) => search(event.target.value)}
            placeholder="Search by username"
            className="input-base mt-3 w-full"
            maxLength={50}
          />
          {searchResults.length > 0 && (
            <div className="mt-2 rounded border border-border">
              {searchResults.map((person) => (
                <button key={person.username} onClick={() => send(person.username)} className="block w-full px-3 py-2 text-left hover:bg-surface-hover">
                  <span className="font-medium">@{person.username}</span>
                  <span className="ml-2 text-xs text-text-muted">{person.display_name || ''}</span>
                </button>
              ))}
            </div>
          )}
          {error && <div className="mt-2 text-sm text-danger">{error}</div>}
        </div>
        <section>
          <h2 className="px-4 py-3 font-semibold text-text-primary">Incoming</h2>
          {incoming.length === 0 && <p className="px-4 pb-4 text-sm text-text-muted">No pending requests.</p>}
          {incoming.map((request) => <RequestCard key={request.id} request={request} incoming onAction={action} />)}
        </section>
        <section>
          <h2 className="px-4 py-3 font-semibold text-text-primary">Outgoing</h2>
          {outgoing.length === 0 && <p className="px-4 pb-4 text-sm text-text-muted">No outgoing requests.</p>}
          {outgoing.map((request) => <RequestCard key={request.id} request={request} onAction={action} />)}
        </section>
      </div>
    </ChatLayout>
  )
}
