import { useEffect, useState } from 'react'
import { Card, Empty, ErrorNote, Loading, PageHeader } from '../components/ui.jsx'
import { api } from '../lib/api'
import { timeAgo } from '../lib/format'

export default function Notifications() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  const load = () => api.notifications().then(setItems).catch(setError)
  useEffect(() => { load() }, [])

  const readOne = async (id) => {
    await api.markRead(id).catch(setError)
    load()
  }
  const readAll = async () => {
    await api.markAllRead().catch(setError)
    load()
  }

  if (error) return <ErrorNote error={error} />
  if (!items) return <Loading />

  return (
    <>
      <PageHeader
        title="Notifications"
        subtitle="Status changes on your pickups and credits."
        actions={
          items.some((n) => !n.is_read) ? (
            <button className="btn sm" onClick={readAll}>Mark all as read</button>
          ) : null
        }
      />
      {items.length === 0 ? (
        <Card><Empty>No notifications yet.</Empty></Card>
      ) : (
        <Card className="pad0">
          {items.map((n) => (
            <div
              key={n.id}
              onClick={() => !n.is_read && readOne(n.id)}
              style={{
                display: 'flex', gap: 12, padding: '14px 18px',
                borderBottom: '1px solid #1C2836', alignItems: 'flex-start',
                cursor: n.is_read ? 'default' : 'pointer',
              }}
            >
              <div className={n.is_read ? '' : 'unread'}
                   style={{ marginTop: 7, width: 7, height: 7 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, color: n.is_read ? 'var(--mut)' : undefined }}>
                  {n.title}
                </div>
                <div className="mut sm">{n.body}</div>
              </div>
              <div className="xs mut" style={{ whiteSpace: 'nowrap' }}>{timeAgo(n.created_at)}</div>
            </div>
          ))}
        </Card>
      )}
    </>
  )
}
