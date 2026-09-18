import { useEffect, useState } from 'react'
import { Card, Empty, ErrorNote, Loading, PageHeader, Stat } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function Credits() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.credits(), api.creditTransactions()])
      .then(([credits, transactions]) => setData({ credits, transactions }))
      .catch(setError)
  }, [])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { credits, transactions } = data

  return (
    <>
      <PageHeader
        title="My credits"
        subtitle="MedCredits are added after a collector hands the items in and verification passes."
      />
      <div className="grid g3">
        <Stat value={credits.balance} label="Current balance" color="var(--teal)" />
        <Stat value={credits.lifetime_earned} label="Lifetime earned" />
        <Stat value={credits.pending} label="Pending verification" color="var(--amber)" />
      </div>

      <Card style={{ marginTop: 16 }}>
        <div className="between">
          <h3>How credits are earned</h3>
          <span className="pill p-grey">
            {credits.credits_per_verified_return} per verified return
          </span>
        </div>
        <p className="mut sm" style={{ margin: '8px 0 0' }}>
          Uploading a photo earns nothing on its own. Credits are written only once a pickup
          reaches COLLECTED and an operator marks the items VERIFIED. The rate is set in the
          backend configuration.
        </p>
      </Card>

      <Card className="pad0" style={{ marginTop: 16 }}>
        <div style={{ padding: '16px 18px' }}><h3>Transaction history</h3></div>
        {transactions.length === 0 ? (
          <Empty>No credit transactions yet.</Empty>
        ) : (
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Date</th><th>Pickup ID</th><th>Reason</th><th>Status</th>
                    <th style={{ textAlign: 'right' }}>Credits</th></tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id}>
                    <td>{formatDate(t.created_at, true)}</td>
                    <td className="mono">{t.pickup_id}</td>
                    <td className="mut">{t.reason}</td>
                    <td><span className="pill p-green">Awarded</span></td>
                    <td style={{ textAlign: 'right' }} className="mono">+{t.amount}</td>
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
