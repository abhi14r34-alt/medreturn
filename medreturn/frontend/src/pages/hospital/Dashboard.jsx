import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Card, ConfidencePill, ErrorNote, Loading, PageHeader, Stat } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

const COLORS = ['#2DD4BF', '#4C8DFF', '#F5A524', '#3DD68C', '#B78CFF', '#F2545B']

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.hospitalDashboard(), api.wasteEvents({ limit: 10 })])
      .then(([stats, events]) => setData({ stats, events }))
      .catch(setError)
  }, [])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { stats, events } = data
  const daily = Object.entries(stats.daily_counts || {}).map(([date, count]) => ({
    date: date.slice(5), count,
  }))
  const categories = Object.entries(stats.category_distribution || {}).map(([name, value]) => ({
    name, value,
  }))

  return (
    <>
      <PageHeader
        title="Hospital dashboard"
        subtitle="Segregation line activity for this facility."
        actions={<Link className="btn pri sm" to="/hospital/analyze">Analyze an item</Link>}
      />

      <div className="grid g4">
        <Stat value={stats.total_analyzed} label="Total analyzed" />
        <Stat value={stats.accepted} label="Accepted and routed" color="var(--green)" />
        <Stat value={stats.quarantined} label="Held in quarantine" color="var(--amber)" />
        <Stat
          value={stats.average_confidence ? `${Math.round(stats.average_confidence * 100)}%` : '—'}
          label="Average confidence"
        />
      </div>

      <div className="split" style={{ marginTop: 16 }}>
        <Card>
          <h3 style={{ marginBottom: 12 }}>Items analyzed per day</h3>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#16212D', border: '1px solid #25374A' }} />
              <Line type="monotone" dataKey="count" stroke="#2DD4BF" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 12 }}>Category distribution</h3>
          <ResponsiveContainer width="100%" height={210}>
            <PieChart>
              <Pie data={categories} dataKey="value" nameKey="name"
                   innerRadius={52} outerRadius={80} paddingAngle={2}>
                {categories.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#16212D', border: '1px solid #25374A' }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="pad0" style={{ marginTop: 16 }}>
        <div className="between" style={{ padding: '16px 18px' }}>
          <h3>Recent events</h3>
          <Link className="btn sm ghost" to="/hospital/traceability">Traceability</Link>
        </div>
        <div className="tblwrap">
          <table>
            <thead>
              <tr><th>Time</th><th>Event ID</th><th>Category</th><th>Confidence</th>
                  <th>Decision</th><th>Route</th><th>Weight</th><th>Location</th></tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.event_id}>
                  <td className="mut sm">{formatDate(e.created_at, true)}</td>
                  <td className="mono sm">{e.event_id}</td>
                  <td>{e.predicted_class}</td>
                  <td><ConfidencePill value={e.confidence} /></td>
                  <td>
                    <span className={`pill ${e.decision === 'ACCEPTED' ? 'p-green' : 'p-amber'}`}>
                      {e.decision === 'ACCEPTED' ? 'Routed' : 'Quarantined'}
                    </span>
                  </td>
                  <td className="mono sm mut">{e.route}</td>
                  <td className="mono">{e.weight_kg} kg</td>
                  <td className="mut sm">{e.location}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
