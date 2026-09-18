import { useEffect, useState } from 'react'
import { Card, Empty, ErrorNote, Loading, PageHeader, Stat } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

export default function CreditsAdmin() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.allTransactions(), api.adminSettings()])
      .then(([transactions, settings]) => setData({ transactions, settings }))
      .catch(setError)
  }, [])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { transactions, settings } = data
  const total = transactions.reduce((sum, t) => sum + t.amount, 0)

  return (
    <>
      <PageHeader title="Credits and rewards"
                  subtitle="Every credit transaction, and the rate that produced it." />
      <div className="grid g3">
        <Stat value={total} label="Credits distributed" color="var(--teal)" />
        <Stat value={transactions.length} label="Transactions" />
        <Stat value={settings.credits_per_verified_return} label="Credits per verified return" />
      </div>

      <div className="note" style={{ marginTop: 16 }}>
        The reward rate comes from <code>CREDITS_PER_VERIFIED_RETURN</code> in the backend
        environment. Changing it is a deployment action with an audit trail rather than a
        click in a web form.
      </div>

      <Card className="pad0" style={{ marginTop: 16 }}>
        <div style={{ padding: '16px 18px' }}><h3>Transactions</h3></div>
        {transactions.length === 0 ? (
          <Empty>No credits awarded yet.</Empty>
        ) : (
          <div className="tblwrap">
            <table>
              <thead>
                <tr><th>Date</th><th>Pickup</th><th>Reason</th><th>Status</th>
                    <th style={{ textAlign: 'right' }}>Credits</th></tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id}>
                    <td className="mut sm">{formatDate(t.created_at, true)}</td>
                    <td className="mono sm">{t.pickup_id}</td>
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
