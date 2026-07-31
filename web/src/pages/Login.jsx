import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import DebugPanel from '../components/DebugPanel'

export default function Login() {
  const [form, setForm] = useState({ username_or_email: '', password: '' })
  const [result, setResult] = useState({ request: null, response: null, error: null, status: null })
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setResult({ request: form, response: null, error: null, status: null })
    const res = await authApi.login(form)
    setResult({
      request: form,
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
    if (res.status === 200 && res.data?.access_token) {
      login(res.data.access_token, res.data.refresh_token)
      setTimeout(() => navigate('/test/dashboard'), 500)
    }
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Login</h2>
      <p className="text-sm text-gray-500 mb-4">POST /api/v1/auth/login</p>
      <form onSubmit={handleSubmit} className="space-y-3 max-w-md">
        <input name="username_or_email" value={form.username_or_email} onChange={handleChange} placeholder="Username or Email" className="w-full border rounded px-3 py-2 text-sm" required />
        <input name="password" type="password" value={form.password} onChange={handleChange} placeholder="Password" className="w-full border rounded px-3 py-2 text-sm" required />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Login</button>
        {result.status && (
          <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {result.status}
          </span>
        )}
      </form>
      {result.status === 200 && (
        <p className="mt-3 text-sm text-green-600">
          Login successful! JWT stored. <Link to="/test/dashboard" className="underline">Go to Dashboard</Link>
        </p>
      )}
      <p className="mt-3 text-sm text-gray-500">
        Need an account? <Link to="/test/register" className="underline">Register</Link>
      </p>
      <DebugPanel request={result.request} response={result.response} error={result.error} />
    </div>
  )
}