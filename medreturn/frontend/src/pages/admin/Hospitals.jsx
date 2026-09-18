import { useEffect, useState } from 'react'
import { Card, ErrorNote, KV, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'

export default function Hospitals() {
  const [hospitals, setHospitals] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.hospitals().then(setHospitals).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!hospitals) return <Loading />

  return (
    <>
      <PageHeader title="Hospitals" subtitle="Facilities connected to the segregation line." />
      <div className="grid g3">
        {hospitals.map((h) => (
          <Card key={h.id}>
            <div className="between" style={{ marginBottom: 10 }}>
              <h3>{h.name}</h3>
              <span className={`pill ${h.status === 'ACTIVE' ? 'p-green' : 'p-amber'}`}>
                {h.status === 'ACTIVE' ? 'Active' : h.status}
              </span>
            </div>
            <KV label="City">{h.city}</KV>
            <KV label="Beds"><span className="mono">{h.beds}</span></KV>
            <KV label="Contact"><span className="mono sm">{h.contact_email}</span></KV>
          </Card>
        ))}
      </div>
    </>
  )
}
