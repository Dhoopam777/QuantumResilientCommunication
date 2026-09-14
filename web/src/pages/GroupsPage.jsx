import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { conversationApi, groupApi, userApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useChat } from '../context/ChatContext'
import Layout from '../components/Layout'
import Avatar from '../components/common/Avatar'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import EmptyState from '../components/common/EmptyState'
import { SearchIcon } from '../components/icons'

export default function GroupsPage() {
  const { isLoggedIn, user } = useAuth()
  const { selectConversation } = useChat()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [selected, setSelected] = useState([])
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isLoggedIn) return
    conversationApi.list()
      .then((response) => setGroups(response.status === 200 && Array.isArray(response.data)
        ? response.data.filter((item) => item.is_group)
        : []))
      .catch(() => setGroups([]))
  }, [isLoggedIn])

  useEffect(() => {
    if (query.trim().length < 2) {
      setMatches([])
      return
    }
    const timer = setTimeout(async () => {
      const response = await userApi.search(query.trim())
      setMatches(response.status === 200 && Array.isArray(response.data) ? response.data : [])
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  const addSelected = (candidate) => {
    if (candidate.username !== user?.username && !selected.some((item) => item.username === candidate.username)) {
      setSelected((items) => [...items, candidate])
    }
    setQuery('')
    setMatches([])
  }

  const create = async (event) => {
    event.preventDefault()
    setError('')
    if (!name.trim() || selected.length === 0) {
      setError('Enter a group name and select at least one member.')
      return
    }
    setLoading(true)
    const response = await groupApi.create({
      group_name: name.trim(),
      group_description: description.trim() || null,
      members: selected.map((item) => item.username),
    })
    setLoading(false)
    if (response.status === 201) {
      selectConversation(response.data.id)
      navigate('/test/chat')
    } else {
      setError(response.data?.detail || 'Unable to create group.')
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-text-primary">Groups</h1>
          <Link to="/test/chat" className="text-sm text-accent">Back to chats</Link>
        </div>
        <form onSubmit={create} className="bg-surface rounded-xl p-5 shadow-sm">
          <h2 className="font-semibold text-text-primary mb-3">Create Group</h2>
          <div className="grid grid-cols-1 gap-3 mb-4">
            <input className="input input-bordered" placeholder="Group name" value={name} onChange={(event) => setName(event.target.value)} maxLength={255} />
            <textarea className="input input-bordered min-h-20 placeholder-textarea" placeholder="Description (optional)" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1000} />
          </div>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-text-secondary">Search usernames</span>
            <input className="input input-bordered flex-1" placeholder="Search usernames" value={query} onChange={(event) => setQuery(event.target.value)} />
            <SearchIcon className="w-4 h-4 text-text-muted" />
          </div>
          {matches.length > 0 && (
            <div className="mt-2 rounded-xl border border-border divide-y divide-border shadow-sm">
              {matches.map((candidate) => (
                <button type="button" key={candidate.username} onClick={() => addSelected(candidate)} className="w-full flex items-center gap-2 p-2 text-left hover:bg-surface-hover transition-colors">
                  <Avatar name={candidate.display_name || candidate.username} src={candidate.profile_picture_url} size="sm" />
                  <span className="text-sm text-text-primary">@{candidate.username}</span>
                </button>
              ))}
            </div>
          )}
          {selected.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {selected.map((candidate) => (
                <button type="button" key={candidate.username} onClick={() => setSelected((items) => items.filter((item) => item.username !== candidate.username))} className="px-2 py-0.5 rounded-full bg-accent-soft text-xs text-accent">
                  @{candidate.username} ×
                </button>
              ))}
            </div>
          )}
          {error && <p className="text-sm text-danger mt-2">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? <Spinner className="me-2" /> : 'Create Group'}
          </Button>
        </form>
        {groups.length === 0 && !loading && !error && (
          <EmptyState
            icon={<SearchIcon className="w-6 h-6 text-accent" />}
            title="No groups yet"
            description="Create a group to start secure quantum-resilient conversations with multiple participants."
          />
        )}
        <div className="space-y-3">
          {groups.map((group) => (
            <button
              key={group.id}
              type="button"
              onClick={() => {
                selectConversation(group.id)
                navigate('/test/chat')
              }}
              className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface border border-border hover:bg-surface-hover hover:border-border-accent transition-colors shadow-sm"
              aria-label={`View group ${group.group_name || 'untitled'}`}
            >
              <Avatar name={group.group_name || 'Group'} src={group.group_avatar_url} size="md" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-text-primary truncate">{group.group_name || 'Group'}</div>
                <div className="text-xs text-text-muted">
                  {group.participants?.length || 0} members
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </Layout>
  )
}