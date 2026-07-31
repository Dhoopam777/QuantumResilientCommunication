import { useState, useEffect } from 'react'
import { authApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

export default function Dashboard() {
  const { isLoggedIn } = useAuth()
  const [result, setResult] = useState({ response: null, error: null, status: null })

  const fetchMe = async () => {
    setResult({ response: null, error: null, status: null })
    const res = await authApi.me()
    setResult({
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }

  useEffect(() => {
    if (isLoggedIn) fetchMe()
  }, [isLoggedIn])

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Dashboard (Current User)</h2>
      <p className="text-sm text-gray-500 mb-4">GET /api/v1/auth/me</p>
      <button onClick={fetchMe} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 mb-4">
        Refresh
      </button>
      {result.status && (
        <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
          Status: {result.status}
        </span>
      )}
      {result.response && result.status === 200 && (
        <div className="bg-white border rounded p-4 mb-4">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="font-semibold text-gray-600">ID</dt>
            <dd className="text-gray-800">{result.response.id}</dd>
            <dt className="font-semibold text-gray-600">Username</dt>
            <dd className="text-gray-800">{result.response.username}</dd>
            <dt className="font-semibold text-gray-600">Email</dt>
            <dd className="text-gray-800">{result.response.email}</dd>
            <dt className="font-semibold text-gray-600">Full Name</dt>
            <dd className="text-gray-800">{result.response.full_name || '—'}</dd>
            <dt className="font-semibold text-gray-600">Active</dt>
            <dd className="text-gray-800">{String(result.response.is_active)}</dd>
            <dt className="font-semibold text-gray-600">Verified</dt>
            <dd className="text-gray-800">{String(result.response.is_verified)}</dd>
            <dt className="font-semibold text-gray-600">Created At</dt>
            <dd className="text-gray-800">{result.response.created_at}</dd>
          </dl>
        </div>
      )}
      <DebugPanel response={result.response} error={result.error} />
    </div>
  )
}