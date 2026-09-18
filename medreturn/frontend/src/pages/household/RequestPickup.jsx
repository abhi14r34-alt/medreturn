import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Card, ErrorNote, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/auth.jsx'
import { todayISO } from '../../lib/format'

const SLOTS = ['09:00-12:00', '10:00-13:00', '14:00-17:00', '17:00-20:00']

export default function RequestPickup() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const returnId = params.get('return_id')

  const [form, setForm] = useState({
    address: user.address || '',
    contact_phone: user.phone || '',
    preferred_date: todayISO(),
    time_slot: SLOTS[0],
    item_count: 1,
    approx_weight_kg: 0.2,
    notes: '',
  })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async () => {
    setError(null)
    setBusy(true)
    try {
      const pickup = await api.createPickup({
        ...form,
        item_count: Number(form.item_count),
        approx_weight_kg: Number(form.approx_weight_kg),
        return_id: returnId ? Number(returnId) : null,
      })
      navigate(`/app/pickups/${pickup.pickup_id}`)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Request a pickup"
        subtitle="A collector comes to your address. Nothing needs to be posted."
      />
      <div className="split">
        <Card>
          <ErrorNote error={error} />
          <div className="fld">
            <label htmlFor="addr">Pickup address</label>
            <textarea id="addr" value={form.address} onChange={set('address')} />
          </div>
          <div className="fld">
            <label htmlFor="ph">Contact number</label>
            <input id="ph" value={form.contact_phone} onChange={set('contact_phone')} />
          </div>
          <div className="grid g2">
            <div className="fld">
              <label htmlFor="date">Preferred date</label>
              <input id="date" type="date" min={todayISO()}
                     value={form.preferred_date} onChange={set('preferred_date')} />
            </div>
            <div className="fld">
              <label htmlFor="slot">Time slot</label>
              <select id="slot" value={form.time_slot} onChange={set('time_slot')}>
                {SLOTS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="grid g2">
            <div className="fld">
              <label htmlFor="items">Number of items</label>
              <input id="items" type="number" min="1" max="99"
                     value={form.item_count} onChange={set('item_count')} />
            </div>
            <div className="fld">
              <label htmlFor="wt">Approx. weight (kg)</label>
              <input id="wt" type="number" step="0.05" min="0.05"
                     value={form.approx_weight_kg} onChange={set('approx_weight_kg')} />
            </div>
          </div>
          <div className="fld">
            <label htmlFor="notes">Notes for the collector</label>
            <textarea id="notes" value={form.notes} onChange={set('notes')}
                      placeholder="Gate code, loose syringes, broken glass" />
          </div>
          <button className="btn pri" style={{ width: '100%' }} disabled={busy} onClick={submit}>
            {busy ? 'Creating…' : 'Confirm pickup request'}
          </button>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 10 }}>What happens next</h3>
          <ol className="mut sm" style={{ paddingLeft: 18, lineHeight: 1.9, margin: 0 }}>
            <li>You get a pickup ID straight away.</li>
            <li>Operations confirm the slot and assign a collector.</li>
            <li>You can follow the pickup on a map on the day.</li>
            <li>The collector checks the items at handover.</li>
            <li>Credits are added once verification passes.</li>
          </ol>
          <div className="sep" />
          <h3 style={{ marginBottom: 8 }}>Please don't include</h3>
          <p className="mut sm" style={{ margin: 0 }}>
            Loose needles outside a puncture-proof container, cytotoxic drugs, or controlled
            substances. Those need a facility handover — call 1800-123-4567.
          </p>
        </Card>
      </div>
    </>
  )
}
