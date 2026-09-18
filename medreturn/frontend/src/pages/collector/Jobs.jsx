import { useEffect, useState } from 'react'
import { Card, Empty, ErrorNote, KV, Loading, PageHeader, StagePill } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

// The only transitions a collector can make from the field.
const NEXT_ACTION = {
  ASSIGNED: ['ON_THE_WAY', 'Start pickup'],
  ON_THE_WAY: ['ARRIVED', 'Mark arrived'],
  ARRIVED: ['COLLECTED', 'Mark collected'],
}

export default function Jobs() {
  const [jobs, setJobs] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)

  const load = () => api.collectorPickups().then(setJobs).catch(setError)
  useEffect(() => { load() }, [])

  const act = async (pickupId, status) => {
    setBusy(pickupId)
    setError(null)
    try {
      await api.collectorStatus(pickupId, status)
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  if (error && !jobs) return <ErrorNote error={error} />
  if (!jobs) return <Loading />

  return (
    <>
      <PageHeader title="Today's pickups" subtitle="Jobs assigned to you." />
      <ErrorNote error={error} />

      {jobs.length === 0 ? (
        <Card>
          <Empty title="No jobs assigned">
            Assigned pickups appear here. An admin can assign one from pickup management.
          </Empty>
        </Card>
      ) : (
        <div className="grid g2">
          {jobs.map((p) => {
            const action = NEXT_ACTION[p.status]
            return (
              <Card key={p.pickup_id}>
                <div className="between" style={{ marginBottom: 10 }}>
                  <span className="mono">{p.pickup_id}</span>
                  <StagePill status={p.status} />
                </div>
                <KV label="Phone"><span className="mono sm">{p.contact_phone || '—'}</span></KV>
                <KV label="Slot">{formatDate(p.preferred_date)} · {p.time_slot}</KV>
                <KV label="Items">{p.item_count} · {p.approx_weight_kg} kg</KV>
                <KV label="Address">
                  <span style={{ textAlign: 'right', display: 'inline-block', maxWidth: '58%' }}>
                    {p.address}
                  </span>
                </KV>
                {p.notes && <div className="note" style={{ marginTop: 10 }}>{p.notes}</div>}

                <div className="row" style={{ marginTop: 12, flexWrap: 'wrap' }}>
                  {action && (
                    <button className="btn pri sm" disabled={busy === p.pickup_id}
                            onClick={() => act(p.pickup_id, action[0])}>
                      {action[1]}
                    </button>
                  )}
                  <a
                    className="btn sm"
                    target="_blank"
                    rel="noreferrer"
                    href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.address)}`}
                  >
                    Navigate
                  </a>
                </div>

                {p.status === 'ARRIVED' && (
                  <p className="xs mut" style={{ margin: '10px 0 0' }}>
                    After collecting, the job moves to pending verification. Credits are
                    released by operations, not from here.
                  </p>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </>
  )
}
