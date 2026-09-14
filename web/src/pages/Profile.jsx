import { useState, useEffect } from 'react'
import { profileApi } from '../lib/api'
import { cryptoApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import ChatLayout from '../components/chat/ChatLayout'
import ProfileHeader from '../components/profile/ProfileHeader'
import ProfileForm from '../components/profile/ProfileForm'
import ProfileStats from '../components/profile/ProfileStats'

export default function Profile() {
  const { isLoggedIn, user, setUser, logout } = useAuth()
  const [result, setResult] = useState({ response: null, error: null, status: null })
  const [saving, setSaving] = useState(false)
  const [pqc, setPqc] = useState(null)
  const [sessions, setSessions] = useState([])

  useEffect(() => {
    if (!user?.username) return
    cryptoApi.publicKey(user.username).then((res) => {
      if (res.status === 200) setPqc(res.data)
    })
    cryptoApi.sessions().then((res) => {
      if (res.status === 200) setSessions(res.data || [])
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
      search=""
      onSearchChange={() => {}}
      sidebarContent={null}
    >
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <ProfileHeader user={user} />
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mt-6">
            <div className="lg:col-span-3">
              <ProfileForm user={user} onSave={handleSave} saving={saving} />
            </div>
            <div className="lg:col-span-2">
              <ProfileStats user={user} />
              {pqc ? (
                <div className="mt-6 bg-surface rounded-xl border border-border p-4">
                  <h3 className="font-semibold text-sm text-text-primary uppercase tracking-wide">Quantum Security</h3>
                  <div className="mt-2 text-xs text-text-secondary space-y-1">
                    <div>Algorithms: {pqc.algorithm_version}</div>
                    <div>Key Created: {pqc.created_at ? new Date(pqc.created_at).toLocaleDateString() : 'available'}</div>
                    <div>Quantum Session: {sessions.some((session) => session.status === 'active') ? 'Active' : 'Not established'}</div>
                    {sessions[0] && (
                      <div>
                        <div>Session Algorithm: {sessions[0].algorithm}</div>
                        <div>Session Created: {new Date(sessions[0].created_at).toLocaleDateString()}</div>
                        <div>Session Expires: {new Date(sessions[0].expires_at).toLocaleDateString()}</div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-xs text-text-muted">Quantum identity keys are unavailable.</p>
              )}
            </div>
          </div>
          {result.status && (
            <div className="mt-4 px-4 py-2">
              <span className={`text-sm ${result.status < 300 ? 'text-success' : 'text-danger'}`}>
                Status: {result.status}
              </span>
            </div>
          )}
        </div>
      </div>
    </ChatLayout>
  )
}