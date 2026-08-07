import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { conversationApi, groupApi, userApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import Layout from '../components/Layout'
import Avatar from '../components/common/Avatar'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'

export default function GroupsPage() {
  const { isLoggedIn, user } = useAuth()
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
      navigate(`/test/chat/${response.data.id}`)
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
        <form onSubmit={create} className="bg-surface border border-border rounded-xl p-5 space-y-3">
          <h2 className="font-semibold text-text-primary">Create Group</h2>
          <input className="input" placeholder="Group name" value={name} onChange={(event) => setName(event.target.value)} maxLength={255} />
          <textarea className="input min-h-20" placeholder="Description (optional)" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1000} />
          <input className="input" placeholder="Search usernames" value={query} onChange={(event) => setQuery(event.target.value)} />
          {matches.length > 0 && (
            <div className="border border-border rounded-lg divide-y divide-border">
              {matches.map((candidate) => (
                <button type="button" key={candidate.username} onClick={() => addSelected(candidate)} className="w-full flex items-center gap-2 p-2 text-left hover:bg-surface-hover">
                  <Avatar name={candidate.display_name || candidate.username} src={candidate.profile_picture_url} size="sm" />
                  <span className="text-sm text-text-primary">@{candidate.username}</span>
                </button>
              ))}
            </div>
          )}
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selected.map((candidate) => (
                <button type="button" key={candidate.username} onClick={() => setSelected((items) => items.filter((item) => item.username !== candidate.username))} className="px-2 py-1 rounded-full bg-accent-soft text-sm text-accent">
                  @{candidate.username} ×
                </button>
              ))}
            </div>
          )}
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={loading}>{loading ? <Spinner /> : 'Create'}</Button>
        </form>
        <div className="space-y-2">
          {groups.map((group) => (
            <Link key={group.id} to={`/test/chat/${group.id}`} className="flex items-center gap-3 p-3 bg-surface border border-border rounded-lg hover:bg-surface-hover">
              <Avatar name={group.group_name || 'Group'} src={group.group_avatar_url} size="md" />
              <div>
                <div className="font-medium text-text-primary">{group.group_name || 'Group'}</div>
                <div className="text-xs text-text-muted">{group.participants?.length || 0} members</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </Layout>
  )
}
