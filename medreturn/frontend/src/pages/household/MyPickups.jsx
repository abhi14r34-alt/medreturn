import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Empty, ErrorNote, Loading, PageHeader, StagePill } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function MyPickups() {
  const [pickups, setPickups] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.myPickups().then(setPickups).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!pickups) return <Loading />

  return (
    <>
      <PageHeader
        title="My pickups"
        subtitle="Every request you have made."
        actions={<Link className="btn pri sm" to="/app/analyze">New return</Link>}
      />
      {pickups.length === 0 ? (
        <Card>
          <Empty title="No pickups yet"
                 action={<Link className="btn pri" to="/app/analyze">Scan a medicine</Link>}>
            Scan a medicine and we'll come and collect it.
          </Empty>
        </Card>
      ) : (
        <Card className="pad0">
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Pickup ID</th><th>Date</th><th>Slot</th><th>Items</th><th>Status</th><th /></tr>
              </thead>
              <tbody>
                {pickups.map((p) => (
                  <tr key={p.pickup_id}>
                    <td className="mono">{p.pickup_id}</td>
                    <td>{formatDate(p.preferred_date)}</td>
                    <td className="mut">{p.time_slot}</td>
                    <td className="mono">{p.item_count}</td>
                    <td><StagePill status={p.status} /></td>
                    <td style={{ textAlign: 'right' }}>
                      <Link className="btn sm" to={`/app/pickups/${p.pickup_id}`}>Track</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  )
}
