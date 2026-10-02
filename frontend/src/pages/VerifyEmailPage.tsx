import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [state, setState] = useState<'working' | 'done' | 'error'>('working')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setState('error')
      setMessage('This verification link is missing its token — open the exact link from your email.')
      return
    }
    api.verifyEmail(token)
      .then((d: any) => {
        setState('done')
        setMessage(`Email verified for ${d?.data?.username || 'your account'}. You're all set.`)
      })
      .catch((e: any) => {
        setState('error')
        setMessage(e.message || 'Verification failed — the link may have expired.')
      })
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '24px', background: 'var(--bg, #0C0E0A)' }}>
      <div className="card" style={{ padding: '36px 32px', maxWidth: '440px', width: '100%', textAlign: 'center' }}>
        <div style={{ fontSize: '2.2rem', marginBottom: '8px' }}>{state === 'working' ? '⏳' : state === 'done' ? '✅' : '⚠️'}</div>
        <h2 style={{ margin: '0 0 6px', fontSize: '1.3rem' }}>
          {state === 'working' ? 'Verifying your email…' : state === 'done' ? 'Email verified' : 'Verification problem'}
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: '0.84rem', lineHeight: 1.6 }}>{message}</p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '18px', flexWrap: 'wrap' }}>
          {state === 'done' ? (
            <button className="btn-primary" onClick={() => navigate('/login')}>Go to sign in</button>
          ) : state === 'error' ? (
            <>
              <Link to="/login" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-block', padding: '10px 20px' }}>Back to sign in</Link>
              <button onClick={() => navigate('/login')}>Resend later</button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
