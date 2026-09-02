import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import Input from '../components/common/Input'
import Button from '../components/common/Button'
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
      setTimeout(() => navigate('/test/chat'), 500)
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h2 className="text-2xl font-bold text-text-primary mb-2">Welcome back</h2>
      <p className="text-sm text-text-secondary mb-6">Sign in to your QRC account</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Username or Email"
          name="username_or_email"
          value={form.username_or_email}
          onChange={handleChange}
          placeholder="username or email"
          required
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
        <Button type="submit" className="w-full">Sign In</Button>
        {result.status && (
          <span className={`text-sm ${result.status < 300 ? 'text-success' : 'text-danger'}`}>
            Status: {result.status}
          </span>
        )}
      </form>

      {result.status === 200 && (
        <p className="mt-3 text-sm text-success">
          Login successful! Redirecting to chat...
        </p>
      )}

      <p className="mt-4 text-sm text-text-secondary">
        Need an account? <Link to="/test/register" className="text-accent hover:underline">Register</Link>
      </p>
      <p className="mt-2 text-sm text-text-secondary">
        Didn&apos;t receive your verification email?{' '}
        <Link to="/test/resend-verification" className="text-accent hover:underline">Resend it</Link>
      </p>

      <DebugPanel request={result.request} response={result.response} error={result.error} />
    </div>
  )
}