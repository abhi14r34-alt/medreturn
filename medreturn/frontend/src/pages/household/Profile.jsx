import { useState } from 'react'
import { Card, ErrorNote, KV, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/auth.jsx'
import { formatDate } from '../../lib/format'

export default function Profile() {
  const { user, setUser, logout } = useAuth()
  const [form, setForm] = useState({
    full_name: user.full_name,
    phone: user.phone || '',
    address: user.address || '',
  })
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) => {
    setSaved(false)
    setForm({ ...form, [key]: e.target.value })
  }

  const save = async () => {
    setError(null)
    setBusy(true)
    try {
      setUser(await api.updateProfile(form))
      setSaved(true)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Profile" subtitle="Where the collector comes and how we reach you." />
      <div className="split">
        <Card>
          <ErrorNote error={error} />
          {saved && <div className="ok">Profile saved.</div>}
          <div className="fld">
            <label htmlFor="name">Full name</label>
            <input id="name" value={form.full_name} onChange={set('full_name')} />
          </div>
          <div className="fld">
            <label htmlFor="phone">Phone</label>
            <input id="phone" value={form.phone} onChange={set('phone')} />
          </div>
          <div className="fld">
            <label htmlFor="addr">Default pickup address</label>
            <textarea id="addr" value={form.address} onChange={set('address')} />
          </div>
          <button className="btn pri" disabled={busy} onClick={save}>
            {busy ? 'Saving…' : 'Save changes'}
          </button>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 10 }}>Account</h3>
          <KV label="Username"><span className="mono">{user.username}</span></KV>
          <KV label="Email"><span className="mono">{user.email}</span></KV>
          <KV label="Role">Household user</KV>
          <KV label="Joined">{formatDate(user.created_at)}</KV>
          <div className="sep" />
          <p className="mut sm">
            Your address is shared only with the collector assigned to your pickup and the
            operations team. It is not shown to other users or hospitals.
          </p>
          <button className="btn danger sm" style={{ marginTop: 8 }} onClick={logout}>
            Sign out
          </button>
        </Card>
      </div>
    </>
  )
}
