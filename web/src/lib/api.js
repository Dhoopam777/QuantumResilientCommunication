const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
let authFailureHandler = null

export const getAccessToken = () => localStorage.getItem('qrc_access_token') || ''
export const getRefreshToken = () => localStorage.getItem('qrc_refresh_token') || ''
export const setTokens = (access, refresh) => {
  localStorage.setItem('qrc_access_token', access)
  if (refresh) localStorage.setItem('qrc_refresh_token', refresh)
}
export const clearTokens = () => {
  localStorage.removeItem('qrc_access_token')
  localStorage.removeItem('qrc_refresh_token')
}
export const getLastConversationId = () => localStorage.getItem('qrc_last_conversation')
export const setLastConversationId = (id) => localStorage.setItem('qrc_last_conversation', id)
export const clearLastConversationId = () => localStorage.removeItem('qrc_last_conversation')
export const setOnAuthFailure = (handler) => { authFailureHandler = handler }

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const headers = { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) }
  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  let data = null
  try { data = await response.json() } catch { /* empty response */ }
  if (response.status === 401 && authFailureHandler) authFailureHandler()
  return { status: response.status, data }
}

export const authApi = {
  login: (payload) => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload) => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  refresh: (refresh_token) => request('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
  me: () => request('/auth/me'),
  verifyEmail: (token) => request(`/auth/verify-email?token=${encodeURIComponent(token)}`),
  resendVerification: (email) => request('/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) }),
}

export const profileApi = {
  update: (payload) => request('/auth/me', { method: 'PUT', body: JSON.stringify(payload) }),
}

export const cryptoApi = {
  publicKey: (username) => request(`/crypto/public-key/${encodeURIComponent(username)}`),
  uploadDeviceKeys: (payload) => request('/crypto/device-keys', { method: 'PUT', body: JSON.stringify(payload) }),
  establishSession: (username, payload) => request(`/crypto/session/${encodeURIComponent(username)}`, { method: 'POST', body: JSON.stringify(payload) }),
  sessions: () => request('/crypto/sessions'),
}

export const userApi = {
  search: (query) => request(`/users/search?q=${encodeURIComponent(query)}`),
}

export const conversationRequestApi = {
  incoming: () => request('/conversation-requests/incoming'),
  outgoing: () => request('/conversation-requests/outgoing'),
  create: (username) => request('/conversation-requests', { method: 'POST', body: JSON.stringify({ username }) }),
  accept: (id) => request(`/conversation-requests/${encodeURIComponent(id)}/accept`, { method: 'POST' }),
  decline: (id) => request(`/conversation-requests/${encodeURIComponent(id)}/decline`, { method: 'POST' }),
  cancel: (id) => request(`/conversation-requests/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}

export const conversationApi = {
  list: () => request('/conversations/'),
  get: (id) => request(`/conversations/${encodeURIComponent(id)}`),
  create: (payload) => request('/conversations/', { method: 'POST', body: JSON.stringify(payload) }),
}

export const groupApi = {
  create: (payload) => request('/groups', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id) => request(`/groups/${encodeURIComponent(id)}`),
  update: (id, payload) => request(`/groups/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  addMember: (id, username) => request(`/groups/${encodeURIComponent(id)}/members`, { method: 'POST', body: JSON.stringify({ username }) }),
  removeMember: (id, username) => request(`/groups/${encodeURIComponent(id)}/members/${encodeURIComponent(username)}`, { method: 'DELETE' }),
}

export const messageApi = {
  list: (conversationId) => request(`/messages/conversation/${encodeURIComponent(conversationId)}`),
  send: (payload) => request('/messages/', { method: 'POST', body: JSON.stringify(payload) }),
  edit: (id, payload) => request(`/messages/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  delete: (id, mode) => request(`/messages/${encodeURIComponent(id)}`, { method: 'DELETE', body: JSON.stringify({ mode }) }),
  toggleReaction: (id, emoji) => request(`/messages/${encodeURIComponent(id)}/reactions`, { method: 'POST', body: JSON.stringify({ emoji }) }),
  removeReaction: (id, emoji) => request(`/messages/${encodeURIComponent(id)}/reactions`, { method: 'DELETE', body: JSON.stringify({ emoji }) }),
}

export const attachmentApi = {
  upload: async (formData) => request('/attachments/upload', { method: 'POST', body: formData }),
  download: async (id) => {
    const token = getAccessToken()
    const response = await fetch(`${API_BASE}/attachments/${encodeURIComponent(id)}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    return { status: response.status, blob: response.ok ? await response.blob() : null }
  },
  delete: (id) => request(`/attachments/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
