import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Timeline from '../../components/Timeline.jsx'
import { Card, Empty, ErrorNote, KV, Loading, PageHeader, Stat, StagePill } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/auth.jsx'
import { formatDate } from '../../lib/format'

const ACTIVE = ['REQUESTED', 'SCHEDULED', 'ASSIGNED', 'ON_THE_WAY', 'ARRIVED', 'COLLECTED', 'VERIFIED']

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.myPickups(), api.credits(), api.returnHistory()])
      .then(([pickups, credits, returns]) => setData({ pickups, credits, returns }))
      .catch(setError)
  }, [])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { pickups, credits, returns } = data
  const active = pickups.find((p) => ACTIVE.includes(p.status))
  const next = pickups
    .filter((p) => ACTIVE.includes(p.status))
    .sort((a, b) => a.preferred_date.localeCompare(b.preferred_date))[0]
  const completed = pickups.filter((p) => p.status === 'COMPLETED')
  const items = completed.reduce((sum, p) => sum + p.item_count, 0)
  const kg = completed.reduce((sum, p) => sum + p.approx_weight_kg, 0)

  return (
    <>
      <PageHeader
        title={`Welcome, ${user.full_name.split(' ')[0]}`}
        subtitle="Everything you have returned, and anything on its way."
        actions={<Link className="btn pri" to="/app/analyze">Scan a medicine</Link>}
      />

      <div className="grid g4">
        <Stat value={credits.balance} label="MedCredits balance" color="var(--teal)" />
        <Stat value={items} label="Items returned" />
        <Stat value={`${kg.toFixed(2)} kg`} label="Kept out of general waste" />
        <Stat value={credits.pending} label="Credits pending verification" color="var(--amber)" />
      </div>

      <div className="split" style={{ marginTop: 16 }}>
        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Next pickup</h3>
            {next && <StagePill status={next.status} />}
          </div>
          {next ? (
            <>
              <KV label="Pickup ID"><span className="mono">{next.pickup_id}</span></KV>
              <KV label="Date">{formatDate(next.preferred_date)}</KV>
              <KV label="Time slot">{next.time_slot}</KV>
              <KV label="Collector">{next.collector?.name || 'Not assigned yet'}</KV>
              <Link className="btn blue sm" style={{ marginTop: 14 }}
                    to={`/app/pickups/${next.pickup_id}`}>
                Track this pickup
              </Link>
            </>
          ) : (
            <Empty action={<Link className="btn pri sm" to="/app/analyze">Scan a medicine</Link>}>
              Nothing scheduled.
            </Empty>
          )}
        </Card>

        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Active request</h3>
            <Link className="btn sm ghost" to="/app/pickups">All pickups</Link>
          </div>
          {active ? (
            <>
              <div className="mono" style={{ fontSize: 19, marginBottom: 6 }}>{active.pickup_id}</div>
              <p className="mut sm">
                {active.item_count} item(s) · {active.approx_weight_kg} kg · {active.time_slot}
              </p>
              <div className="sep" />
              <Timeline status={active.status} />
            </>
          ) : (
            <Empty>No active request.</Empty>
          )}
        </Card>
      </div>

      <Card className="pad0" style={{ marginTop: 16 }}>
        <div className="between" style={{ padding: '16px 18px' }}>
          <h3>Recent returns</h3>
          <Link className="btn sm ghost" to="/app/history">Full history</Link>
        </div>
        {returns.length === 0 ? (
          <Empty>No returns yet.</Empty>
        ) : (
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Item</th><th>Category</th><th>Confidence</th><th>Status</th><th>Pickup</th></tr>
              </thead>
              <tbody>
                {returns.slice(0, 6).map((r) => (
                  <tr key={r.id}>
                    <td>{r.detected_item}</td>
                    <td className="mut">{r.category}</td>
                    <td className="mono">{Math.round((r.confidence || 0) * 100)}%</td>
                    <td>
                      <span className={`pill ${r.eligibility_status === 'ELIGIBLE' ? 'p-green' : 'p-amber'}`}>
                        {r.eligibility_status === 'ELIGIBLE' ? 'Eligible' : 'Needs review'}
                      </span>
                    </td>
                    <td className="mono sm">{r.pickup_id || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
