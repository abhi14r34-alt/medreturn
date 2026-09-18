import { useEffect, useState } from 'react'
import { Card, ConfidencePill, Empty, ErrorNote, KV, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function Quarantine() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = () => api.quarantine(true).then(setItems).catch(setError)
  useEffect(() => { load() }, [])

  const decide = async (quarantineId, release) => {
    setBusyId(quarantineId)
    setError(null)
    try {
      await api.verifyQuarantine(quarantineId, { release })
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusyId(null)
    }
  }

  if (error && !items) return <ErrorNote error={error} />
  if (!items) return <Loading />

  return (
    <>
      <PageHeader
        title="Quarantine"
        subtitle="Items the model was not confident enough to route. A person decides what happens next."
        actions={<span className="pill p-amber">{items.length} awaiting review</span>}
      />
      <ErrorNote error={error} />

      {items.length === 0 ? (
        <Card>
          <Empty title="Quarantine is clear">Nothing is waiting for a decision right now.</Empty>
        </Card>
      ) : (
        <div className="grid g2">
          {items.map((item) => (
            <Card key={item.quarantine_id}>
              <div className="between" style={{ marginBottom: 10 }}>
                <span className="mono sm">{item.event.event_id}</span>
                <span className="pill p-amber">Quarantined</span>
              </div>
              <KV label="Predicted class">{item.event.predicted_class}</KV>
              <KV label="Confidence"><ConfidencePill value={item.event.confidence} /></KV>
              <KV label="Reason held">
                <span style={{ textAlign: 'right', display: 'inline-block', maxWidth: '58%' }}>
                  {item.reason}
                </span>
              </KV>
              <KV label="Logged">{formatDate(item.event.created_at, true)}</KV>
              <KV label="Location">{item.event.location}</KV>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="btn pri sm" disabled={busyId === item.quarantine_id}
                        onClick={() => decide(item.quarantine_id, true)}>
                  Verify and release
                </button>
                <button className="btn sm" disabled={busyId === item.quarantine_id}
                        onClick={() => decide(item.quarantine_id, false)}>
                  Keep quarantined
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
