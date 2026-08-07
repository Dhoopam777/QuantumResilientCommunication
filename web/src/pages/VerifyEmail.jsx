import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authApi } from '../lib/api'
import Spinner from '../components/common/Spinner'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const [state, setState] = useState('loading')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setState('expired')
      return
    }
    authApi.verifyEmail(token).then((response) => {
      setState(response.status === 200 ? 'success' : 'expired')
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
          <p className="mt-2 text-text-secondary">Sign in and request a new verification email.</p>
          <Link to="/test/login" className="btn-primary inline-block mt-5">Sign in</Link>
        </>
      )}
    </div>
  )
}
