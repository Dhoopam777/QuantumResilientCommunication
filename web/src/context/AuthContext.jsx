import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  clearLastConversationId,
  authApi,
  setOnAuthFailure,
} from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(getAccessToken())
  const [refreshToken, setRefreshToken] = useState(getRefreshToken())
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // Reference to the active WebSocket client so logout can close it
  const wsClientRef = useRef(null)

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
   *   2. If 401, try to refresh the access token and retry /auth/me.
   *   3. If refresh fails, clear tokens (user must log in again).
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

      // Access token is invalid/expired — try to refresh it
      const refresh = getRefreshToken()
      if (!refresh) {
        // No refresh token — session is invalid
        logout()
        if (!cancelled) setLoading(false)
        return
      }

      try {
        const res = await authApi.refresh(refresh)
        if (cancelled) return

        if (res.status === 200 && res.data?.access_token) {
          setTokens(res.data.access_token, refresh)
          setAccessToken(res.data.access_token)
          // Retry loading the user with the new token
          const retryUser = await loadCurrentUser()
          if (!cancelled) {
            if (!retryUser) {
              logout()
            }
            setLoading(false)
          }
        } else {
          // Refresh failed — session is invalid
          logout()
          if (!cancelled) setLoading(false)
        }
      } catch (err) {
        logout()
        if (!cancelled) setLoading(false)
      }
    }

    // Register the auth failure callback so api.js can trigger logout
    // when a token refresh fails during any API call.
    setOnAuthFailure(() => {
      logout()
      setLoading(false)
    })

    validateSession()

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
   * Refresh the access token manually (used by WebSocket re-auth).
   * @returns {Promise<string|null>} The new access token, or null on failure
   */
  const refreshAccessToken = useCallback(async () => {
    const refresh = getRefreshToken()
    if (!refresh) return null

    try {
      const res = await authApi.refresh(refresh)
      if (res.status === 200 && res.data?.access_token) {
        setTokens(res.data.access_token, refresh)
        setAccessToken(res.data.access_token)
        return res.data.access_token
      }
      return null
    } catch (err) {
      return null
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