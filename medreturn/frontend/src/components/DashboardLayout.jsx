import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import TopBar from './TopBar.jsx'
import { api } from '../lib/api'

const NAVS = {
  household: [
    ['Dashboard', '/app'],
    ['Medicine Analyzer', '/app/analyze'],
    ['Request Pickup', '/app/request'],
    ['My Pickups', '/app/pickups'],
    ['My Credits', '/app/credits'],
    ['Return History', '/app/history'],
    ['Notifications', '/app/notifications'],
    ['Profile', '/app/profile'],
  ],
  hospital: [
    ['Dashboard', '/hospital'],
    ['AI Waste Analyzer', '/hospital/analyze'],
    ['Quarantine', '/hospital/quarantine'],
    ['Traceability', '/hospital/traceability'],
    ['Bin Status', '/hospital/bins'],
    ['Model Information', '/hospital/model'],
    ['Notifications', '/hospital/notifications'],
  ],
  admin: [
    ['Dashboard', '/admin'],
    ['Pickup Management', '/admin/pickups'],
    ['Users', '/admin/users'],
    ['Hospitals', '/admin/hospitals'],
    ['Credits & Rewards', '/admin/credits'],
    ['Email Log', '/admin/emails'],
    ['AI Model', '/admin/model'],
    ['System Settings', '/admin/settings'],
  ],
  collector: [
    ["Today's Pickups", '/collector'],
    ['Notifications', '/collector/notifications'],
  ],
}

export default function DashboardLayout({ section }) {
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    api.unreadCount().then((d) => setUnread(d.unread)).catch(() => {})
  }, [])

  return (
    <>
      <TopBar />
      <div className="shell">
        <aside className="side">
          <div className="grp">{section.toUpperCase()}</div>
          {NAVS[section].map(([label, path]) => (
            <NavLink
              key={path}
              to={path}
              end={path.split('/').length === 2}
              className={({ isActive }) => (isActive ? 'on' : '')}
            >
              {label}
              {path.endsWith('/notifications') && unread > 0 && (
                <span className="pill p-teal" style={{ marginLeft: 'auto' }}>{unread}</span>
              )}
            </NavLink>
          ))}
        </aside>
        <main className="main"><Outlet /></main>
      </div>
    </>
  )
}
