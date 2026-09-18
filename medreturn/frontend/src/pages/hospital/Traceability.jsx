import { useEffect, useState } from 'react'
import { Card, ConfidencePill, Empty, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

const CLASSES = ['Sharps', 'Infectious', 'Pharmaceutical', 'Glass', 'Plastic Recyclable', 'General']

export default function Traceability() {
  const [filters, setFilters] = useState({
    predicted_class: '', decision: '', location: '', min_confidence: '',
  })
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      api.wasteEvents(filters).then(setRows).catch(setError)
    }, 250) // debounce the location text field
    return () => clearTimeout(timer)
  }, [filters])

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.value })

  return (
    <>
      <PageHeader
        title="Traceability"
        subtitle="Search the full event record by category, location, decision or confidence."
      />
      <Card style={{ marginBottom: 16 }}>
        <div className="grid g4">
          <div className="fld">
            <label htmlFor="loc">Location</label>
            <input id="loc" placeholder="e.g. Lab Inlet"
                   value={filters.location} onChange={set('location')} />
          </div>
          <div className="fld">
            <label htmlFor="cls">Category</label>
            <select id="cls" value={filters.predicted_class} onChange={set('predicted_class')}>
              <option value="">All categories</option>
              {CLASSES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="fld">
            <label htmlFor="dec">Decision</label>
            <select id="dec" value={filters.decision} onChange={set('decision')}>
              <option value="">All decisions</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="QUARANTINED">Quarantined</option>
            </select>
          </div>
          <div className="fld">
            <label htmlFor="conf">Minimum confidence</label>
            <select id="conf" value={filters.min_confidence} onChange={set('min_confidence')}>
              <option value="">Any</option>
              <option value="0.6">60% and above</option>
              <option value="0.8">80% and above</option>
              <option value="0.9">90% and above</option>
            </select>
          </div>
        </div>
      </Card>

      <ErrorNote error={error} />
      {!rows ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Card><Empty title="No matching events">Widen the filters to see more of the record.</Empty></Card>
      ) : (
        <Card className="pad0">
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Event ID</th><th>Timestamp</th><th>Category</th><th>Weight</th>
                    <th>Location</th><th>Confidence</th><th>Decision</th><th>Verification</th></tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.event_id}>
                    <td className="mono sm">{e.event_id}</td>
                    <td className="mut sm">{formatDate(e.created_at, true)}</td>
                    <td>{e.predicted_class}</td>
                    <td className="mono">{e.weight_kg} kg</td>
                    <td className="mut sm">{e.location}</td>
                    <td><ConfidencePill value={e.confidence} /></td>
                    <td>
                      <span className={`pill ${e.decision === 'ACCEPTED' ? 'p-green' : 'p-amber'}`}>
                        {e.decision === 'ACCEPTED' ? 'Accepted' : 'Quarantined'}
                      </span>
                    </td>
                    <td className="sm mut">{e.verification_status || 'Not required'}</td>
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
