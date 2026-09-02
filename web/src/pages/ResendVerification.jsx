import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../lib/api'
import Input from '../components/common/Input'
import Button from '../components/common/Button'

export default function ResendVerification() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState(null) // { kind: 'sent' | 'error', text }
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setMessage(null)
    const res = await authApi.resendVerification(email)
    setSubmitting(false)
    if (res.status === 200) {
      setMessage({ kind: 'sent', text: res.data?.detail || 'If that email belongs to an unverified account, a fresh verification link has been sent.' })
    } else {
      setMessage({ kind: 'error', text: res.data?.detail || 'Unable to resend verification email. Please try again later.' })
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h2 className="text-2xl font-bold text-text-primary mb-2">Resend verification email</h2>
      <p className="text-sm text-text-secondary mb-6">
        Enter the email address you registered with. If the account is not verified yet, a fresh
        verification link will be sent to it.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Email"
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoComplete="email"
          required
        />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? 'Sending…' : 'Send verification email'}
        </Button>
      </form>

      {message && (
        <p className={`mt-4 text-sm ${message.kind === 'sent' ? 'text-success' : 'text-danger'}`}>
          {message.text}
        </p>
      )}

      <p className="mt-4 text-sm text-text-secondary">
        Remembered your password? <Link to="/test/login" className="text-accent hover:underline">Sign in</Link>
      </p>
    </div>
  )
}