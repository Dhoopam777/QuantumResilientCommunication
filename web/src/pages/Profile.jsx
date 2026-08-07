import { useState, useEffect } from 'react'
import { profileApi } from '../lib/api'
import { cryptoApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import ChatLayout from '../components/chat/ChatLayout'
import ProfileHeader from '../components/profile/ProfileHeader'
import ProfileForm from '../components/profile/ProfileForm'
import ProfileStats from '../components/profile/ProfileStats'
import DebugPanel from '../components/DebugPanel'

export default function Profile() {
  const { isLoggedIn, user, setUser, logout } = useAuth()
  const [result, setResult] = useState({ response: null, error: null, status: null })
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [pqc, setPqc] = useState(null)

  useEffect(() => {
    if (!user?.username) return
    cryptoApi.publicKey(user.username).then((res) => {
      if (res.status === 200) setPqc(res.data)
    })
  }, [user?.username])

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  const handleSave = async (formData) => {
    setSaving(true)
    setResult({ response: null, error: null, status: null })
    const res = await profileApi.update(formData)
    setSaving(false)
    setResult({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
    if (res.status === 200 && res.data) {
      setUser(res.data)
    }
  }

  return (
    <ChatLayout
      user={user}
      onLogout={logout}
      search={search}
      onSearchChange={setSearch}
      sidebarContent={null}
    >
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          <ProfileHeader user={user} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
            <div className="border-r border-border">
              <ProfileForm user={user} onSave={handleSave} saving={saving} />
            </div>
            <div>
              <ProfileStats user={user} />
              <div className="p-4 border-t border-border">
                <h3 className="font-semibold text-sm text-text-primary">Quantum Security</h3>
                {pqc ? (
                  <div className="mt-2 text-xs text-text-secondary space-y-1">
                    <div>Algorithms: {pqc.algorithm_version}</div>
                    <div>Key Created: {user.pq_key_created_at ? new Date(user.pq_key_created_at).toLocaleDateString() : 'available'}</div>
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-text-muted">Quantum identity keys are unavailable.</p>
                )}
              </div>
            </div>
          </div>
          {result.status && (
            <div className="px-4 py-2">
              <span className={`text-sm ${result.status < 300 ? 'text-success' : 'text-danger'}`}>
                Status: {result.status}
              </span>
            </div>
          )}
          <DebugPanel response={result.response} error={result.error} />
        </div>
      </div>
    </ChatLayout>
  )
}