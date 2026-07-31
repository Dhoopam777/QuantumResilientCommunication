import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../lib/api'
import DebugPanel from '../components/DebugPanel'

export default function Register() {
  const [form, setForm] = useState({
    username: '',
    email: '',
    full_name: '',
    profile_picture_url: '',
    password: '',
    is_active: true,
    is_verified: false,
  })
  const [result, setResult] = useState({ request: null, response: null, error: null, status: null })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setResult({ request: form, response: null, error: null, status: null })
    const res = await authApi.register(form)
    setResult({
      request: form,
      response: res.data,
      error: res.error || (res.status >= 400 ? JSON.stringify(res.data) : null),
      status: res.status,
    })
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Register</h2>
      <p className="text-sm text-gray-500 mb-4">POST /api/v1/auth/register</p>
      <form onSubmit={handleSubmit} className="space-y-3 max-w-md">
        <input name="username" value={form.username} onChange={handleChange} placeholder="Username" className="w-full border rounded px-3 py-2 text-sm" required />
        <input name="email" type="email" value={form.email} onChange={handleChange} placeholder="Email" className="w-full border rounded px-3 py-2 text-sm" required />
        <input name="full_name" value={form.full_name} onChange={handleChange} placeholder="Full Name" className="w-full border rounded px-3 py-2 text-sm" />
        <input name="profile_picture_url" value={form.profile_picture_url} onChange={handleChange} placeholder="Profile Picture URL" className="w-full border rounded px-3 py-2 text-sm" />
        <input name="password" type="password" value={form.password} onChange={handleChange} placeholder="Password" className="w-full border rounded px-3 py-2 text-sm" required />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} /> is_active
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="is_verified" checked={form.is_verified} onChange={handleChange} /> is_verified
        </label>
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Register</button>
        {result.status && (
          <span className={`ml-3 text-sm ${result.status < 300 ? 'text-green-600' : 'text-red-600'}`}>
            Status: {result.status}
          </span>
        )}
      </form>
      {result.status === 201 && (
        <p className="mt-3 text-sm text-green-600">
          Registration successful! <Link to="/test/login" className="underline">Go to Login</Link>
        </p>
      )}
      <DebugPanel request={result.request} response={result.response} error={result.error} />
    </div>
  )
}