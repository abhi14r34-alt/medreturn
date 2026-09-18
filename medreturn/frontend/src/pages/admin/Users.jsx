import { useEffect, useState } from 'react'
import { Card, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { formatDate } from '../../lib/format'

const ROLE_TONE = { admin: 'p-red', hospital: 'p-blue', collector: 'p-amber', household: 'p-teal' }

export default function Users() {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.users().then(setUsers).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!users) return <Loading />

  return (
    <>
      <PageHeader title="Users" subtitle="Every account on the platform." />
      <Card className="pad0">
        <div className="tblwrap">
          <table>
            <thead>
              <tr><th>Name</th><th>Username</th><th>Email</th><th>Role</th><th>Joined</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td className="mono sm">{u.username}</td>
                  <td className="mut sm">{u.email}</td>
                  <td><span className={`pill ${ROLE_TONE[u.role]}`}>{u.role}</span></td>
                  <td className="mut sm">{formatDate(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <p className="xs mut" style={{ marginTop: 10 }}>
        Household addresses are not listed here. They are revealed only to the collector
        assigned to a specific pickup.
      </p>
    </>
  )
}
