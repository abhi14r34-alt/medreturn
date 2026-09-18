import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Card, ErrorNote, KV, Loading, PageHeader, Stat } from '../../components/ui.jsx'
import { api } from '../../lib/api'

const COLORS = ['#2DD4BF', '#4C8DFF', '#F5A524', '#3DD68C', '#B78CFF', '#F2545B']

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.adminDashboard().then(setStats).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!stats) return <Loading />

  const categories = Object.entries(stats.category_distribution || {})
    .map(([name, value]) => ({ name, value }))
  const byStatus = Object.entries(stats.pickups_by_status || {})
    .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))

  return (
    <>
      <PageHeader title="Admin dashboard"
                  subtitle="Platform-wide activity across households and hospitals." />

      <div className="grid g4">
        <Stat value={stats.household_returns} label="Household returns" />
        <Stat value={stats.waste_events} label="Hospital waste events" />
        <Stat value={stats.quarantined_open} label="Awaiting quarantine review" color="var(--amber)" />
        <Stat value={stats.credits_distributed} label="Credits distributed" color="var(--teal)" />
      </div>

      <div className="grid g4" style={{ marginTop: 14 }}>
        <Stat value={stats.pickups_total} label="Pickups requested" />
        <Stat value={stats.pickups_completed} label="Pickups completed" color="var(--green)" />
        <Stat value={`${stats.completion_rate}%`} label="Completion rate" />
        <Stat
          value={stats.average_confidence ? `${Math.round(stats.average_confidence * 100)}%` : '—'}
          label="Average AI confidence"
        />
      </div>

      <div className="split" style={{ marginTop: 16 }}>
        <Card>
          <h3 style={{ marginBottom: 12 }}>Pickups by stage</h3>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={byStatus}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" interval={0} angle={-25} textAnchor="end" height={70} />
              <YAxis allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#16212D', border: '1px solid #25374A' }} />
              <Bar dataKey="value" fill="#4C8DFF" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 12 }}>Waste category distribution</h3>
          <ResponsiveContainer width="100%" height={230}>
            <PieChart>
              <Pie data={categories} dataKey="value" nameKey="name"
                   innerRadius={54} outerRadius={84} paddingAngle={2}>
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

      <Card style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Needs your attention</h3>
        <KV label="Unassigned requests">
          <span className="mono">{stats.pickups_by_status?.REQUESTED || 0}</span>
        </KV>
        <KV label="Awaiting verification">
          <span className="mono">{stats.pickups_by_status?.COLLECTED || 0}</span>
        </KV>
        <KV label="Quarantined items">
          <span className="mono">{stats.quarantined_open}</span>
        </KV>
        <div className="row" style={{ marginTop: 14, flexWrap: 'wrap' }}>
          <Link className="btn pri sm" to="/admin/pickups">Manage pickups</Link>
          <Link className="btn sm" to="/hospital/quarantine">Review quarantine</Link>
        </div>
      </Card>
    </>
  )
}
