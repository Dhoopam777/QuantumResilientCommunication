import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import {
  authApi,
  clearLastConversationId,
  clearTokens,
  decodeJwtPayload,
  getAccessToken,
  getRefreshToken,
  refreshAccessToken as apiRefreshAccessToken,
  setOnAuthFailure,
  setOnTokenRefresh,
  setTokens,
} from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(getAccessToken())
  const [refreshToken, setRefreshToken] = useState(getRefreshToken())
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // Reference to the active WebSocket client so logout can close it
  const wsClientRef = useRef(null)
  // Proactive access-token refresh timer (fires ~60s before expiry)
  const refreshTimerRef = useRef(null)
  const refreshRetryRef = useRef(0)

  /**
   * Register a WebSocket client so logout can close it.
   * Called by ChatWindow when it creates a WebSocket connection.
   */
  const registerWebSocket = useCallback((wsClient) => {
    wsClientRef.current = wsClient
  }, [])

  /**
   * Unregister the WebSocket client (called on ChatWindow unmount).
   */
  const unregisterWebSocket = useCallback(() => {
    wsClientRef.current = null
  }, [])

  /**
   * Clear all auth state and cached data.
   */
  const logout = useCallback(() => {
    // Clean up any pending proactive refresh and refuse stale refreshes.
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
    refreshRetryRef.current = 0
    clearTokens()
    clearLastConversationId()
    setAccessToken('')
    setRefreshToken('')
    setUser(null)
    // Close the WebSocket if one is active
    if (wsClientRef.current) {
      wsClientRef.current.disconnect()
      wsClientRef.current = null
    }
  }, [])

  /**
   * Load the current user profile from the server.
   * @returns {Promise<object|null>} The user object, or null on failure
   */
  const loadCurrentUser = useCallback(async () => {
    const res = await authApi.me()
    if (res.status === 200 && res.data) {
      setUser(res.data)
      return res.data
    }
    return null
  }, [])

  /**
   * Validate the session on mount:
   *   1. If tokens exist, call /auth/me to verify the access token.
   *   2. The API layer automatically refreshes on a 401 and retries, so a
   *      successful /auth/me means the session is valid (possibly after refresh).
   *   3. If validation still fails, the session is gone — log out.
   */
  useEffect(() => {
    let cancelled = false

    const validateSession = async () => {
      const token = getAccessToken()
      if (!token) {
        if (!cancelled) setLoading(false)
        return
      }

      // Try to load the current user with the existing access token
      const userData = await loadCurrentUser()
      if (cancelled) return

      if (userData) {
        setLoading(false)
        return
      }

      // Auto-refresh already failed inside the API layer — session is invalid.
      logout()
      if (!cancelled) setLoading(false)
    }

    validateSession()

    // Register the auth-failure callback so api.js can trigger logout when a
    // token refresh fails during any API call.
    setOnAuthFailure(() => {
      logout()
      setLoading(false)
    })

    // Forward successfully refreshed access tokens into React state so that
    // consumers (e.g. ChatPage) can re-authenticate the WebSocket via
    // reconnectWithToken().
    setOnTokenRefresh((newToken) => {
      setAccessToken(newToken)
    })

    return () => {
      cancelled = true
    }
  }, [loadCurrentUser, logout])

  /**
   * Login: store tokens and load the user profile.
   */
  const login = useCallback(
    async (access, refresh) => {
      setTokens(access, refresh)
      setAccessToken(access)
      setRefreshToken(refresh)
      await loadCurrentUser()
    },
    [loadCurrentUser],
  )

  /**
   * Refresh the access token and publish the result to React state.
   * The single-flight refresh itself lives in api.js; this wrapper keeps the
   * existing refreshAccessToken context API intact (used by WebSocket re-auth).
   * @returns {Promise<string|null>} The new access token, or null on failure
   */
  const refreshAccessToken = useCallback(async () => {
    const newToken = await apiRefreshAccessToken()
    if (newToken) setAccessToken(newToken)
    return newToken
  }, [])

  /**
   * Proactively refresh ~60 seconds before the access token expires so the
   * user is never forced to log in again every 15 minutes.
   */
  const runProactiveRefresh = useCallback(async () => {
    const newToken = await refreshAccessToken()
    if (newToken) return
    // Bounded background retries for transient failures; the reactive
    // 401-refresh in api.js covers any remaining cases.
    if (refreshRetryRef.current >= 5) return
    refreshRetryRef.current += 1
    refreshTimerRef.current = setTimeout(() => {
      runProactiveRefresh()
    }, 60 * 1000)
  }, [refreshAccessToken])

  const scheduleTokenRefresh = useCallback((token) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
    refreshRetryRef.current = 0
    if (!token) return

    const payload = decodeJwtPayload(token)
    const expSec = payload?.exp
    if (!expSec) return

    const delayMs = expSec * 1000 - Date.now() - 60 * 1000
    if (delayMs <= 0) {
      runProactiveRefresh()
      return
    }
    refreshTimerRef.current = setTimeout(() => {
      runProactiveRefresh()
    }, delayMs)
  }, [runProactiveRefresh])

  // (Re)schedule the proactive refresh whenever the access token changes.
  useEffect(() => {
    scheduleTokenRefresh(accessToken)
  }, [accessToken, scheduleTokenRefresh])

  // Clean up any pending refresh timer when the provider unmounts.
  useEffect(() => () => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  const isLoggedIn = Boolean(accessToken) && !loading

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        accessToken,
        refreshToken,
        loading,
        isLoggedIn,
        login,
        logout,
        refreshAccessToken,
        registerWebSocket,
        unregisterWebSocket,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}