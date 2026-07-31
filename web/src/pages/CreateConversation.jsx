import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { conversationApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

export default function CreateConversation() {
  const { isLoggedIn } = useAuth()
  const [participantIds, setParticipantIds] = useState('')
  const [isGroup, setIsGroup] = useState(false)
  const [groupName, setGroupName] = useState('')
  const [result, setResult] = useState({ request: null, response: null, error: null, status: null })
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    const ids = participantIds
      .split(/[,\n\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    const payload = {
      participant_ids: ids,
      is_group: isGroup,
      group_name: isGroup ? groupName : null,
    }
    setResult({ request: payload, response: null, error: null, status: null })
    const res = await conversationApi.create(payload)
    setResult({
      request: payload,
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
    if (res.status === 201 && res.data?.id) {
      setTimeout(() => navigate(`/test/conversations/${res.data.id}`), 800)
    }
  }

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Create Conversation</h2>
      <p className="text-sm text-gray-500 mb-4">POST /api/v1/conversations/</p>
      <form onSubmit={handleSubmit} className="space-y-3 max-w-md">
        <div>
          <label className="text-sm font-semibold text-gray-600">Participant IDs (comma or newline separated UUIDs)</label>
          <textarea
            value={participantIds}
            onChange={(e) => setParticipantIds(e.target.value)}
            placeholder="e.g. 603fb9dc-ac33-47af-bebe-a25246b98d09"
            className="w-full border rounded px-3 py-2 text-sm mt-1"
            rows={3}
            required
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isGroup} onChange={(e) => setIsGroup(e.target.checked)} /> is_group
        </label>
        {isGroup && (
          <input
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            placeholder="Group Name"
            className="w-full border rounded px-3 py-2 text-sm"
          />
        )}
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Create</button>
        {result.status && (
          <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {result.status}
          </span>
        )}
      </form>
      {result.status === 201 && (
        <p className="mt-3 text-sm text-green-600">
          Conversation created! <Link to="/test/conversations" className="underline">Back to list</Link>
        </p>
      )}
      <DebugPanel request={result.request} response={result.response} error={result.error} />
    </div>
  )
}