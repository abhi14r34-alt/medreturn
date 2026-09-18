import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Card, ErrorNote } from '../components/ui.jsx'
import { HOME_FOR_ROLE, useAuth } from '../lib/auth.jsx'

const BLANK = {
  full_name: '',
  username: '',
  email: '',
  phone: '',
  address: '',
  password: '',
}

export default function Register() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(BLANK)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={HOME_FOR_ROLE[user.role] || '/'} replace />

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async () => {
    setError(null)
    // Check the obvious things here so the user is not waiting on a round trip.
    if (form.password.length < 8) {
      setError(new Error('Use a password of at least 8 characters.'))
      return
    }
    if (form.address.trim().length < 10) {
      setError(new Error('Enter a full pickup address so the collector can find you.'))
      return
    }
    setBusy(true)
    try {
      await register({ ...form, phone: form.phone || null })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ maxWidth: 470, margin: '0 auto', padding: '48px 22px' }}>
      <h1 style={{ marginBottom: 6 }}>Create your account</h1>
      <p className="mut sm" style={{ marginBottom: 20 }}>
        Household accounts only. Hospital, collector and admin logins are issued by the
        operations team.
      </p>

      <Card>
        <ErrorNote error={error} />
        <div className="fld">
          <label htmlFor="name">Full name</label>
          <input id="name" value={form.full_name} onChange={set('full_name')} />
        </div>
        <div className="fld">
          <label htmlFor="user">Username</label>
          <input id="user" value={form.username} onChange={set('username')} />
        </div>
        <div className="fld">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={form.email} onChange={set('email')} />
        </div>
        <div className="fld">
          <label htmlFor="phone">Phone</label>
          <input id="phone" value={form.phone} onChange={set('phone')} />
        </div>
        <div className="fld">
          <label htmlFor="address">Default pickup address</label>
          <textarea id="address" value={form.address} onChange={set('address')} />
        </div>
        <div className="fld">
          <label htmlFor="pw">Password</label>
          <input
            id="pw"
            type="password"
            value={form.password}
            onChange={set('password')}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>
        <button className="btn pri" style={{ width: '100%' }} disabled={busy} onClick={submit}>
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <p className="xs mut" style={{ margin: '12px 0 0' }}>
          Your address goes to the collection team so they can find you. It is not shown to
          other users.
        </p>
      </Card>
    </div>
  )
}
