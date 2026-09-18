import { useEffect, useState } from 'react'
import { Card, Empty, ErrorNote, KV, Loading, PageHeader, StagePill } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate, STAGES, stageIndex } from '../../lib/format'

const FILTERS = [
  ['', 'All'],
  ['REQUESTED', 'Pending'],
  ['SCHEDULED', 'Scheduled'],
  ['ASSIGNED', 'Assigned'],
  ['ON_THE_WAY', 'On the way'],
  ['COLLECTED', 'To verify'],
  ['COMPLETED', 'Completed'],
]

export default function PickupManagement() {
  const [filter, setFilter] = useState('')
  const [pickups, setPickups] = useState(null)
  const [collectors, setCollectors] = useState([])
  const [selected, setSelected] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)

  const load = () => api.adminPickups(filter).then(setPickups).catch(setError)

  useEffect(() => { setPickups(null); load() }, [filter])
  useEffect(() => { api.collectors().then(setCollectors).catch(() => {}) }, [])

  const assign = async (pickupId) => {
    const collectorId = selected[pickupId]
    if (!collectorId) {
      setError(new Error('Choose a collector first.'))
      return
    }
    setBusy(pickupId)
    setError(null)
    try {
      await api.assignCollector(pickupId, Number(collectorId))
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  const advance = async (pickup) => {
    const next = STAGES[stageIndex(pickup.status) + 1]
    if (!next) return
    setBusy(pickup.pickup_id)
    setError(null)
    try {
      await api.updatePickupStatus(pickup.pickup_id, { status: next[0] })
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Pickup management"
        subtitle="Assign a collector, move the status on, verify items and release credits."
      />
      <div className="chips">
        {FILTERS.map(([value, label]) => (
          <button key={label} className={`chip ${filter === value ? 'on' : ''}`}
                  onClick={() => setFilter(value)}>
            {label}
          </button>
        ))}
      </div>

      <ErrorNote error={error} />

      {!pickups ? (
        <Loading />
      ) : pickups.length === 0 ? (
        <Card><Empty>No pickups in this state.</Empty></Card>
      ) : (
        <div className="grid g2">
          {pickups.map((p) => {
            const next = STAGES[stageIndex(p.status) + 1]
            const isBusy = busy === p.pickup_id
            return (
              <Card key={p.pickup_id}>
                <div className="between" style={{ marginBottom: 10 }}>
                  <span className="mono">{p.pickup_id}</span>
                  <StagePill status={p.status} />
                </div>
                <KV label="Requested slot">
                  {formatDate(p.preferred_date)} · {p.time_slot}
                </KV>
                <KV label="Items">{p.item_count} · {p.approx_weight_kg} kg</KV>
                <KV label="Collector">{p.collector?.name || 'Unassigned'}</KV>
                <KV label="Address">
                  <span style={{ textAlign: 'right', display: 'inline-block', maxWidth: '58%' }}>
                    {p.address}
                  </span>
                </KV>
                {p.notes && (
                  <KV label="Notes">
                    <span style={{ textAlign: 'right', display: 'inline-block', maxWidth: '58%' }}>
                      {p.notes}
                    </span>
                  </KV>
                )}

                <div className="sep" style={{ margin: '12px 0' }} />
                <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
                  <select
                    style={{ width: 'auto', flex: 1, minWidth: 140, padding: '7px 10px' }}
                    value={selected[p.pickup_id] || p.collector?.id || ''}
                    onChange={(e) => setSelected({ ...selected, [p.pickup_id]: e.target.value })}
                  >
                    <option value="">Assign collector…</option>
                    {collectors.map((c) => (
                      <option key={c.id} value={c.id}>{c.name} · {c.zone}</option>
                    ))}
                  </select>
                  <button className="btn sm" disabled={isBusy} onClick={() => assign(p.pickup_id)}>
                    Assign
                  </button>
                  {next && p.status !== 'COMPLETED' && (
                    <button className="btn pri sm" disabled={isBusy} onClick={() => advance(p)}>
                      {next[0] === 'CREDITS_AWARDED' ? 'Award credits'
                        : next[0] === 'VERIFIED' ? 'Verify items'
                        : `Set ${next[1].toLowerCase()}`}
                    </button>
                  )}
                </div>

                {p.status === 'COLLECTED' && (
                  <p className="xs mut" style={{ margin: '10px 0 0' }}>
                    Verification confirms the items match the request. Credits are only
                    written after this step.
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
