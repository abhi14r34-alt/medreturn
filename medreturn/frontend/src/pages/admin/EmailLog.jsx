import { useEffect, useState } from 'react'
import { Card, DemoTag, Empty, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function EmailLog() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.emailLog().then(setRows).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!rows) return <Loading />

  const consoleOnly = rows.every((r) => r.transport === 'console')

  return (
    <>
      <PageHeader
        title="Email log"
        subtitle="Every notification the system queued."
        actions={consoleOnly ? <DemoTag>NO SMTP CONFIGURED</DemoTag> : null}
      />
      <div className="note" style={{ marginBottom: 16 }}>
        The email service is an abstraction. With SMTP settings blank, messages are composed
        and logged but not sent. Fill in the SMTP variables in the backend <code>.env</code>
        to deliver them for real. Credentials never live in client code.
      </div>

      {rows.length === 0 ? (
        <Card><Empty>No emails queued yet.</Empty></Card>
      ) : (
        <Card className="pad0">
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Queued</th><th>To</th><th>Subject</th><th>Pickup</th>
                    <th>Transport</th><th>Delivery</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="mut sm">{formatDate(r.created_at, true)}</td>
                    <td className="mono sm">{r.recipient}</td>
                    <td>{r.subject}</td>
                    <td className="mono sm">{r.pickup_id || '—'}</td>
                    <td className="mut sm">{r.transport}</td>
                    <td>
                      <span className={`pill ${r.delivered ? 'p-green' : 'p-grey'}`}>
                        {r.delivered ? 'Sent' : 'Not sent'}
                      </span>
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
