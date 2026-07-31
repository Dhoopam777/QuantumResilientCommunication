import { useState } from 'react'
import { authApi, getAccessToken, getRefreshToken } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

function decodeJwtPayload(token) {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(payload)
  } catch {
    return null
  }
}

export default function TokenViewer() {
  const { isLoggedIn, logout } = useAuth()
  const [refreshResult, setRefreshResult] = useState({ request: null, response: null, error: null, status: null })

  const accessToken = getAccessToken()
  const refreshToken = getRefreshToken()
  const accessPayload = decodeJwtPayload(accessToken)
  const refreshPayload = decodeJwtPayload(refreshToken)

  const handleRefresh = async () => {
    const res = await authApi.refresh(refreshToken)
    setRefreshResult({
      request: { refresh_token: refreshToken },
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Token Viewer</h2>

      {/* Access Token */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-600 mb-1">Access Token</h3>
        <pre className="bg-gray-900 text-green-400 text-xs rounded p-3 overflow-auto max-h-32 break-all">
          {accessToken}
        </pre>
        {accessPayload && (
          <div className="mt-2">
            <h4 className="text-xs font-semibold text-gray-500 mb-1">Decoded Payload</h4>
            <pre className="bg-gray-100 text-gray-800 text-xs rounded p-3 overflow-auto max-h-48">
              {JSON.stringify(accessPayload, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Refresh Token */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-600 mb-1">Refresh Token</h3>
        <pre className="bg-gray-900 text-green-400 text-xs rounded p-3 overflow-auto max-h-32 break-all">
          {refreshToken}
        </pre>
        {refreshPayload && (
          <div className="mt-2">
            <h4 className="text-xs font-semibold text-gray-500 mb-1">Decoded Payload</h4>
            <pre className="bg-gray-100 text-gray-800 text-xs rounded p-3 overflow-auto max-h-48">
              {JSON.stringify(refreshPayload, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Refresh action */}
      <div className="mb-4">
        <button onClick={handleRefresh} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          Refresh Access Token
        </button>
        <span className="ml-3 text-sm text-gray-500">POST /api/v1/auth/refresh</span>
        {refreshResult.status && (
          <span className={`ml-3 text-sm ${refreshResult.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {refreshResult.status}
          </span>
        )}
      </div>

      {/* Logout */}
      <div className="mb-4">
        <button onClick={logout} className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700">
          Logout (Clear Tokens)
        </button>
      </div>

      <DebugPanel request={refreshResult.request} response={refreshResult.response} error={refreshResult.error} />
    </div>
  )
}