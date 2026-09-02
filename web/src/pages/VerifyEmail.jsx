import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Spinner from '../components/common/Spinner'
import { authApi } from '../lib/api'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const [state, setState] = useState('loading')
  const submittedTokensRef = useRef(new Set())

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setState('expired')
      return
    }
    if (submittedTokensRef.current.has(token)) return
    submittedTokensRef.current.add(token)
    authApi.verifyEmail(token).then((response) => {
      if (response.status === 200) setState('success')
      else if (response.data?.detail?.includes('already')) setState('used')
      else if (response.data?.detail?.includes('expired')) setState('expired')
      else setState('invalid')
    })
  }, [params])

  return (
    <div className="max-w-md mx-auto text-center">
      {state === 'loading' && <Spinner />}
      {state === 'success' && (
        <>
          <h2 className="text-2xl font-bold text-text-primary">Email verified</h2>
          <p className="mt-2 text-text-secondary">Your account now has full access.</p>
          <Link to="/test/login" className="btn-primary inline-block mt-5">Continue to login</Link>
        </>
      )}
      {state === 'expired' && (
        <>
          <h2 className="text-2xl font-bold text-text-primary">Verification link expired</h2>
          <p className="mt-2 text-text-secondary">Request a new verification email with the email address you registered.</p>
          <Link to="/test/resend-verification" className="btn-primary inline-block mt-5">Resend verification email</Link>
        </>
      )}
      {state === 'used' && (
        <><h2 className="text-2xl font-bold text-text-primary">Verification link already used</h2><p className="mt-2 text-text-secondary">This account has already been verified.</p><Link to="/test/login" className="btn-primary inline-block mt-5">Sign in</Link></>
      )}
      {state === 'invalid' && (
        <><h2 className="text-2xl font-bold text-text-primary">Invalid verification link</h2><p className="mt-2 text-text-secondary">Request a new verification email with the email address you registered.</p><Link to="/test/resend-verification" className="btn-primary inline-block mt-5">Resend verification email</Link></>
      )}
    </div>
  )
}
