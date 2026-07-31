import { useState, useEffect } from 'react'
import { profileApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

export default function Profile() {
  const { isLoggedIn, user, setUser } = useAuth()
  const [formData, setFormData] = useState({
    display_name: '',
    bio: '',
    profile_picture_url: '',
    status_message: '',
  })
  const [result, setResult] = useState({ response: null, error: null, status: null })
  const [copied, setCopied] = useState(false)

  // Sync form with user data from AuthContext
  useEffect(() => {
    if (user) {
      setFormData({
        display_name: user.display_name || '',
        bio: user.bio || '',
        profile_picture_url: user.profile_picture_url || '',
        status_message: user.status_message || '',
      })
    }
  }, [user])

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setResult({ response: null, error: null, status: null })
    const res = await profileApi.update(formData)
    setResult({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
    if (res.status === 200 && res.data) {
      // Update AuthContext user so the header/nav reflect changes immediately
      setUser(res.data)
    }
  }

  const handleCopyId = () => {
    if (user?.id) {
      navigator.clipboard.writeText(user.id)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Generate initials for avatar fallback
  const initials = (user?.display_name || user?.username || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Profile</h2>

      {/* Profile header card */}
      <div className="bg-white border rounded p-4 mb-6 flex items-center gap-4">
        {/* Avatar */}
        {formData.profile_picture_url ? (
          <img
            src={formData.profile_picture_url}
            alt="Profile"
            className="w-16 h-16 rounded-full object-cover border"
          />
        ) : (
          <div className="w-16 h-16 rounded-full bg-blue-600 text-white flex items-center justify-center text-xl font-bold">
            {initials}
          </div>
        )}

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-lg">
              {user?.display_name || user?.username}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${user?.is_online ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {user?.is_online ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="text-gray-500 text-sm">@{user?.username}</div>
          {user?.status_message && (
            <div className="text-gray-600 text-sm mt-1">{user.status_message}</div>
          )}
          {user?.last_seen && (
            <div className="text-gray-400 text-xs mt-1">
              Last seen: {new Date(user.last_seen).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Editable form */}
      <form onSubmit={handleSave} className="space-y-4 max-w-md mb-6">
        <h3 className="font-semibold text-sm">Edit Profile</h3>

        {/* Read-only fields */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Username (read-only)</label>
          <input
            value={user?.username || ''}
            disabled
            className="w-full border rounded px-3 py-2 text-sm bg-gray-50 text-gray-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Email (read-only)</label>
          <input
            value={user?.email || ''}
            disabled
            className="w-full border rounded px-3 py-2 text-sm bg-gray-50 text-gray-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">User ID (read-only)</label>
          <div className="flex gap-2">
            <input
              value={user?.id || ''}
              disabled
              className="flex-1 border rounded px-3 py-2 text-sm bg-gray-50 text-gray-500 font-mono"
            />
            <button
              type="button"
              onClick={handleCopyId}
              className="bg-gray-200 px-3 py-2 rounded text-sm hover:bg-gray-300 whitespace-nowrap"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Editable fields */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Display Name</label>
          <input
            name="display_name"
            value={formData.display_name}
            onChange={handleChange}
            placeholder="Display name shown to others"
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Profile Picture URL</label>
          <input
            name="profile_picture_url"
            value={formData.profile_picture_url}
            onChange={handleChange}
            placeholder="https://..."
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status Message</label>
          <input
            name="status_message"
            value={formData.status_message}
            onChange={handleChange}
            placeholder="What's on your mind?"
            maxLength={200}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Bio</label>
          <textarea
            name="bio"
            value={formData.bio}
            onChange={handleChange}
            placeholder="Tell us about yourself"
            rows={3}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>

        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          Save Profile
        </button>
        {result.status && (
          <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {result.status}
          </span>
        )}
      </form>

      <DebugPanel response={result.response} error={result.error} />
    </div>
  )
}