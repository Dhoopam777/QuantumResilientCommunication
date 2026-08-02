import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../lib/api'
import Input from '../components/common/Input'
import Button from '../components/common/Button'
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
    <div className="max-w-md mx-auto">
      <h2 className="text-2xl font-bold text-text-primary mb-2">Create account</h2>
      <p className="text-sm text-text-secondary mb-6">Join the QRC secure communication platform</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Username"
          name="username"
          value={form.username}
          onChange={handleChange}
          placeholder="Choose a username"
          required
        />
        <Input
          label="Email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          placeholder="you@example.com"
          required
        />
        <Input
          label="Full Name (optional)"
          name="full_name"
          value={form.full_name}
          onChange={handleChange}
          placeholder="Your full name"
        />
        <Input
          label="Profile Picture URL (optional)"
          name="profile_picture_url"
          value={form.profile_picture_url}
          onChange={handleChange}
          placeholder="https://..."
        />
        <Input
          label="Password"
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          placeholder="••••••••"
          required
        />
        <Button type="submit" className="w-full">Create Account</Button>
        {result.status && (
          <span className={`text-sm ${result.status < 300 ? 'text-success' : 'text-danger'}`}>
            Status: {result.status}
          </span>
        )}
      </form>

      {result.status === 201 && (
        <p className="mt-3 text-sm text-success">
          Registration successful! <Link to="/test/login" className="text-accent hover:underline">Go to Login</Link>
        </p>
      )}

      <p className="mt-4 text-sm text-text-secondary">
        Already have an account? <Link to="/test/login" className="text-accent hover:underline">Sign in</Link>
      </p>

      <DebugPanel request={result.request} response={result.response} error={result.error} />
    </div>
  )
}