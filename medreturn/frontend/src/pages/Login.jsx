import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Card, ErrorNote } from '../components/ui.jsx'
import { HOME_FOR_ROLE, useAuth } from '../lib/auth.jsx'

const DEMO_ACCOUNTS = [
  ['rhea', 'Household user'],
  ['operator', 'Hospital operator'],
  ['admin', 'Administrator'],
  ['collector', 'Collector'],
]

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={HOME_FOR_ROLE[user.role] || '/'} replace />

  const submit = async (username, password) => {
    setError(null)
    setBusy(true)
    try {
      const signedIn = await login(username.trim(), password)
      navigate(HOME_FOR_ROLE[signedIn.role] || '/', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', padding: '48px 22px' }}>
      <h1 style={{ marginBottom: 6 }}>Log in</h1>
      <p className="mut sm" style={{ marginBottom: 20 }}>
        Use a demo account below, or the one you created.
      </p>

      <Card>
        <ErrorNote error={error} />
        <div className="fld">
          <label htmlFor="username">Username or email</label>
          <input
            id="username"
            autoComplete="username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && submit(form.username, form.password)}
          />
        </div>
        <div className="fld">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && submit(form.username, form.password)}
          />
        </div>
        <button
          className="btn pri"
          style={{ width: '100%' }}
          disabled={busy}
          onClick={() => submit(form.username, form.password)}
        >
          {busy ? 'Signing in…' : 'Log in'}
        </button>
        <p className="sm mut" style={{ margin: '14px 0 0' }}>
          No account yet? <Link to="/register" style={{ color: 'var(--teal)' }}>Create one</Link>
        </p>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 4 }}>Demo accounts</h3>
        <p className="xs mut" style={{ marginBottom: 10 }}>
          Created by <code>python -m scripts.seed_demo</code>. Password for all four:{' '}
          <code>medreturn123</code>. Tap to fill and sign in.
        </p>
        {DEMO_ACCOUNTS.map(([username, role]) => (
          <div className="kv" key={username}>
            <span>{role}</span>
            <button
              className="btn sm"
              disabled={busy}
              onClick={() => {
                setForm({ username, password: 'medreturn123' })
                submit(username, 'medreturn123')
              }}
            >
              <span className="mono">{username}</span>
            </button>
          </div>
        ))}
      </Card>
    </div>
  )
}
