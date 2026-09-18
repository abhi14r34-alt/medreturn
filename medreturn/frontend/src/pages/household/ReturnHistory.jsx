import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Empty, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

const TONE = { ELIGIBLE: 'p-green', NEEDS_REVIEW: 'p-amber', UNSUPPORTED: 'p-red' }
const LABEL = { ELIGIBLE: 'Eligible', NEEDS_REVIEW: 'Needs review', UNSUPPORTED: 'Unsupported' }

export default function ReturnHistory() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.returnHistory().then(setItems).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!items) return <Loading />

  return (
    <>
      <PageHeader title="Return history"
                  subtitle="Every item you have put through the analyzer." />
      {items.length === 0 ? (
        <Card>
          <Empty title="Nothing scanned yet"
                 action={<Link className="btn pri" to="/app/analyze">Scan a medicine</Link>}>
            Your analyzed items will be listed here.
          </Empty>
        </Card>
      ) : (
        <Card className="pad0">
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Scanned</th><th>Item</th><th>Category</th><th>Confidence</th>
                    <th>Inference</th><th>Eligibility</th><th>Pickup</th><th>Verified</th></tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td className="mut sm">{formatDate(r.created_at)}</td>
                    <td>{r.detected_item}</td>
                    <td className="mut">{r.category}</td>
                    <td className="mono">{Math.round((r.confidence || 0) * 100)}%</td>
                    <td>
                      <span className={`pill ${r.inference_mode === 'DEMO' ? 'p-amber' : 'p-green'}`}>
                        {r.inference_mode}
                      </span>
                    </td>
                    <td>
                      <span className={`pill ${TONE[r.eligibility_status]}`}>
                        {LABEL[r.eligibility_status]}
                      </span>
                    </td>
                    <td className="mono sm">{r.pickup_id || '—'}</td>
                    <td className="mut sm">{r.verified_at ? formatDate(r.verified_at) : '—'}</td>
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
