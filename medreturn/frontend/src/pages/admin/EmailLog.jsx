import { useEffect, useState } from 'react'
import { Card, DemoTag, Empty, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function EmailLog() {
  const [rows, setRows] = useState(null)
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState(null)
  const [testStatus, setTestStatus] = useState(null)
  const [sendingTest, setSendingTest] = useState(false)

  const load = () => Promise.all([api.emailLog(), api.adminSettings()])
    .then(([emailRows, runtimeSettings]) => {
      setRows(emailRows)
      setSettings(runtimeSettings)
    })
    .catch(setError)

  useEffect(() => { load() }, [])

  const sendTest = async () => {
    setSendingTest(true)
    setTestStatus(null)
    try {
      const result = await api.sendTestEmail()
      setTestStatus(
        result.delivered
          ? `Test email sent to ${result.recipient}.`
          : result.transport === 'disabled'
            ? 'Email delivery is disabled on the server.'
            : result.transport === 'smtp'
              ? `SMTP delivery failed${result.error ? `: ${result.error}` : '.'}`
              : 'Test email was logged locally. Configure SMTP to deliver it.',
      )
      await load()
    } catch (requestError) {
      setTestStatus(requestError.message)
    } finally {
      setSendingTest(false)
    }
  }

  if (error) return <ErrorNote error={error} />
  if (!rows || !settings) return <Loading />

  const smtpConfigured = settings.email_transport === 'smtp'

  return (
    <>
      <PageHeader
        title="Email log"
        subtitle="Every notification the system queued."
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {!smtpConfigured && (
              <DemoTag>{settings.email_transport === 'disabled' ? 'EMAIL DISABLED' : 'NO SMTP CONFIGURED'}</DemoTag>
            )}
            <button className="btn pri sm" type="button" onClick={sendTest} disabled={sendingTest}>
              {sendingTest ? 'Sending...' : 'Send test email'}
            </button>
          </div>
        }
      />
      <div className="note" style={{ marginBottom: 16 }}>
        {smtpConfigured
          ? 'SMTP delivery is enabled. Send a test email to verify the current configuration.'
          : 'Messages are composed and logged but not delivered. Fill in the SMTP variables in the backend .env and restart the API. Credentials never live in client code.'}
      </div>
      {testStatus && <div className="note" style={{ marginBottom: 16 }}>{testStatus}</div>}

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
                      {r.error && <div className="xs" style={{ color: 'var(--amber)', marginTop: 4 }}>{r.error}</div>}
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
