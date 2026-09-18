import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Timeline from '../../components/Timeline.jsx'
import { Card, DemoTag, ErrorNote, KV, Loading, PageHeader, StagePill } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

/** Schematic map. A real provider replaces this with tiles and a live route. */
function DemoMap({ tracking }) {
  const hasVehicle = tracking.collector_lat != null
  const progress = hasVehicle ? 0.62 : 0
  const x = 90 + progress * (430 - 90)
  const y = 230 - progress * (230 - 95)

  return (
    <>
      <svg viewBox="0 0 520 300"
           style={{ width: '100%', height: 'auto', background: '#0B131C',
                    borderRadius: 12, border: '1px solid var(--line)' }}>
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0H0V40" fill="none" stroke="#182636" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="520" height="300" fill="url(#grid)" />
        <path d="M60 270 L150 250 L240 200 L330 170 L440 80"
              stroke="#22344a" strokeWidth="16" fill="none" strokeLinecap="round" />
        <path d="M90 230 L200 210 L300 175 L430 95"
              stroke="#4C8DFF" strokeWidth="2.5" fill="none" strokeDasharray="7 5" opacity=".85" />
        <circle cx="430" cy="95" r="9" fill="#2DD4BF" opacity=".25" />
        <circle cx="430" cy="95" r="4.5" fill="#2DD4BF" />
        <text x="430" y="78" fill="#8EA4B8" fontSize="11" textAnchor="middle"
              fontFamily="IBM Plex Mono">Your address</text>
        {hasVehicle && (
          <>
            <circle cx={x} cy={y} r="11" fill="#4C8DFF" opacity=".2" />
            <circle cx={x} cy={y} r="5" fill="#4C8DFF" />
            <text x={x} y={y + 22} fill="#8EA4B8" fontSize="11" textAnchor="middle"
                  fontFamily="IBM Plex Mono">Collector</text>
          </>
        )}
        {tracking.demo && (
          <text x="14" y="288" fill="#F5A524" fontSize="10.5" fontFamily="IBM Plex Mono">
            DEMO TRACKING — SIMULATED POSITION
          </text>
        )}
      </svg>
      <div className="grid g3" style={{ marginTop: 12 }}>
        <div className="card stat" style={{ padding: 13 }}>
          <div className="v" style={{ fontSize: 19 }}>
            {tracking.eta_minutes ? `${tracking.eta_minutes} min` : '—'}
          </div>
          <div className="k">Estimated arrival</div>
        </div>
        <div className="card stat" style={{ padding: 13 }}>
          <div className="v" style={{ fontSize: 19 }}>
            {tracking.distance_km ? `${tracking.distance_km} km` : '—'}
          </div>
          <div className="k">Distance remaining</div>
        </div>
        <div className="card stat" style={{ padding: 13 }}>
          <div className="v" style={{ fontSize: 19 }}>{tracking.status.replace(/_/g, ' ')}</div>
          <div className="k">Stage</div>
        </div>
      </div>
      <p className="xs mut" style={{ marginTop: 10 }}>{tracking.note}</p>
    </>
  )
}

export default function TrackPickup() {
  const { pickupId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.pickup(pickupId), api.tracking(pickupId)])
      .then(([pickup, tracking]) => setData({ pickup, tracking }))
      .catch(setError)
  }, [pickupId])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { pickup, tracking } = data

  return (
    <>
      <PageHeader
        title={`Tracking ${pickup.pickup_id}`}
        subtitle="Status updates as operations and the collector move the job along."
        actions={<Link className="btn sm ghost" to="/app/pickups">All pickups</Link>}
      />
      <div className="split">
        <Card>
          <div className="between" style={{ marginBottom: 14 }}>
            <h3>Progress</h3>
            <StagePill status={pickup.status} />
          </div>
          <Timeline status={pickup.status} history={pickup.history} />
        </Card>

        <div>
          <Card style={{ marginBottom: 14 }}>
            <div className="between" style={{ marginBottom: 10 }}>
              <h3>Live map</h3>
              {tracking.demo && <DemoTag>DEMO TRACKING</DemoTag>}
            </div>
            <DemoMap tracking={tracking} />
          </Card>

          <Card>
            <h3 style={{ marginBottom: 10 }}>Pickup details</h3>
            <KV label="Requested">{formatDate(pickup.created_at, true)}</KV>
            <KV label="Date and slot">
              {formatDate(pickup.preferred_date)} · {pickup.time_slot}
            </KV>
            <KV label="Items">{pickup.item_count} · {pickup.approx_weight_kg} kg</KV>
            <KV label="Collector">
              {pickup.collector ? `${pickup.collector.name} · ${pickup.collector.phone}` : 'Not assigned yet'}
            </KV>
            <KV label="Address">
              <span style={{ textAlign: 'right', display: 'inline-block', maxWidth: '60%' }}>
                {pickup.address}
              </span>
            </KV>
          </Card>
        </div>
      </div>
    </>
  )
}
