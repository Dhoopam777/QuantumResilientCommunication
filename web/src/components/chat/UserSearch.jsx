import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Avatar from '../common/Avatar'
import Spinner from '../common/Spinner'
import { conversationApi, conversationRequestApi, userApi } from '../../lib/api'
import { apiErrorToMessage } from '../../lib/apiErrors'
import { useAuth } from '../../context/AuthContext'
import { useChat } from '../../context/ChatContext'

const MIN_QUERY = 2
const SEARCH_DELAY_MS = 250

/**
 * Username-based user search used to start a 1:1 conversation.
 *
 * Follows the GroupsPage pattern: debounced search via the existing
 * `GET /users/search` endpoint, avatar + @username results, and a selectable
 * result that sends a conversation request (or resumes an existing/incoming
 * one). No UUIDs are displayed or required anywhere in this flow.
 */
export default function UserSearch({ onClose = null }) {
  const { user } = useAuth()
  const { selectConversation } = useChat()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)
  const [status, setStatus] = useState('idle') // idle|sending|sent|already_requested|existing|accepting|accepted|error
  const [statusMessage, setStatusMessage] = useState('')
  const [conversations, setConversations] = useState([])
  const [incoming, setIncoming] = useState([])
  const [outgoing, setOutgoing] = useState([])

  const loadContext = useCallback(async () => {
    const [convRes, inRes, outRes] = await Promise.all([
      conversationApi.list(),
      conversationRequestApi.incoming(),
      conversationRequestApi.outgoing(),
    ])
    if (convRes.status === 200 && Array.isArray(convRes.data)) setConversations(convRes.data)
    if (inRes.status === 200 && Array.isArray(inRes.data)) setIncoming(inRes.data)
    if (outRes.status === 200 && Array.isArray(outRes.data)) setOutgoing(outRes.data)
  }, [])

  useEffect(() => {
    loadContext()
  }, [loadContext])

  // Debounced username search (GroupsPage pattern).
  useEffect(() => {
    const term = query.trim()
    if (term.length < MIN_QUERY) {
      setSearching(false)
      setMatches([])
      return
    }
    setSearching(true)
    const timer = setTimeout(async () => {
      const res = await userApi.search(term)
      setMatches(res.status === 200 && Array.isArray(res.data) ? res.data : [])
      setSearching(false)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [query])

  const findConversationWith = useCallback(
    (username) => conversations.find(
      (c) => !c.is_group && c.participants?.some(
        (p) => p.user_id !== user?.id && p.username === username,
      ),
    ),
    [conversations, user?.id],
  )

  const findIncomingWith = useCallback(
    (username) => incoming.find(
      (r) => r.status === 'PENDING' && r.sender?.username === username,
    ),
    [incoming],
  )

  const findOutgoingWith = useCallback(
    (username) => outgoing.find(
      (r) => r.status === 'PENDING' && r.receiver?.username === username,
    ),
    [outgoing],
  )

  const handleSelect = async (candidate) => {
    setQuery('')
    setMatches([])
    setSelected(candidate)

    // 1. Already in a conversation — jump straight to it.
    const existing = findConversationWith(candidate.username)
    if (existing) {
      setStatus('existing')
      setStatusMessage(`Already have a conversation with @${candidate.username}`)
      selectConversation(existing.id)
      navigate('/test/chat')
      return
    }

    // 2. They already sent us a request — accept it to open the conversation.
    const inRequest = findIncomingWith(candidate.username)
    if (inRequest) {
      setStatus('accepting')
      setStatusMessage(`Accepting @${candidate.username}'s request…`)
      const res = await conversationRequestApi.accept(inRequest.id)
      await loadContext()
      if (res.status === 200) {
        const conv = findConversationWith(candidate.username)
        if (conv) {
          setStatus('accepted')
          setStatusMessage(`Conversation with @${candidate.username} is ready`)
          selectConversation(conv.id)
          navigate('/test/chat')
        } else {
          setStatus('error')
          setStatusMessage('Request accepted, but the conversation could not be opened.')
        }
      } else {
        setStatus('error')
        setStatusMessage(apiErrorToMessage(res.data, 'Unable to accept that request.'))
      }
      return
    }

    // 3. We already sent a request — say so.
    const outRequest = findOutgoingWith(candidate.username)
    if (outRequest) {
      setStatus('already_requested')
      setStatusMessage(`Request already sent to @${candidate.username}`)
      return
    }

    // 4. Otherwise send a new request.
    setStatus('sending')
    setStatusMessage(`Sending request to @${candidate.username}…`)
    const res = await conversationRequestApi.create(candidate.username)
    await loadContext()
    if (res.status === 201) {
      setStatus('sent')
      setStatusMessage(`Request sent to @${candidate.username}`)
      return
    }

    // The request was rejected — reflect any state that may have appeared
    // between our check and the API call.
    const conv = findConversationWith(candidate.username)
    if (conv) {
      setStatus('existing')
      setStatusMessage(`Already have a conversation with @${candidate.username}`)
      selectConversation(conv.id)
      navigate('/test/chat')
      return
    }
    if (findOutgoingWith(candidate.username)) {
      setStatus('already_requested')
      setStatusMessage(`Request already sent to @${candidate.username}`)
      return
    }
    if (findIncomingWith(candidate.username)) {
      setStatus('error')
      setStatusMessage(`You have an incoming request from @${candidate.username} — accept it from the Requests page.`)
      return
    }
    setStatus('error')
    setStatusMessage(apiErrorToMessage(res.data, 'Unable to send the request.'))
  }

  const reset = () => {
    setSelected(null)
    setStatus('idle')
    setStatusMessage('')
    setMatches([])
    setQuery('')
  }

  const term = query.trim()

  return (
    <div className="border-b border-border px-4 py-3 space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">🔍</span>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelected(null)
              setStatus('idle')
              setStatusMessage('')
            }}
            placeholder="Search users by username"
            autoFocus
            className="input-base pl-9"
            aria-label="Search users"
          />
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="icon-btn"
            aria-label="Close search users"
            title="Close"
          >
            ✕
          </button>
        )}
      </div>

      {term.length > 0 && term.length < MIN_QUERY && !selected && (
        <p className="text-xs text-text-muted">Type at least {MIN_QUERY} characters to search.</p>
      )}

      {searching && (
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Spinner size="sm" />
          <span>Searching…</span>
        </div>
      )}

      {!searching && !selected && term.length >= MIN_QUERY && matches.length > 0 && (
        <div className="max-h-40 overflow-y-auto border border-border rounded-lg divide-y divide-border">
          {matches.map((candidate) => (
            <button
              key={candidate.username}
              type="button"
              onClick={() => handleSelect(candidate)}
              className="w-full flex items-center gap-2 p-2 text-left hover:bg-surface-hover"
            >
              <Avatar
                name={candidate.display_name || candidate.username}
                src={candidate.profile_picture_url}
                size="sm"
                online={candidate.status === 'online'}
              />
              <span className="text-sm text-text-primary">@{candidate.username}</span>
              {candidate.display_name && (
                <span className="text-xs text-text-muted truncate">{candidate.display_name}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {!searching && !selected && term.length >= MIN_QUERY && matches.length === 0 && (
        <p className="text-xs text-text-muted">No users found for “{term}”.</p>
      )}

      {selected && statusMessage && (
        <p
          className={`text-sm ${status === 'error' ? 'text-danger' : 'text-success'}`}
          data-testid="user-search-status"
        >
          {apiErrorToMessage(statusMessage)}
        </p>
      )}

      {selected && (
        <button
          type="button"
          onClick={reset}
          className="text-xs text-text-muted underline hover:text-text-primary"
        >
          Search again
        </button>
      )}
    </div>
  )
}