import { Link, Outlet } from 'react-router-dom'
import TopBar from './TopBar.jsx'

export default function PublicLayout() {
  return (
    <>
      <TopBar />
      <Outlet />
      <footer>
        <div className="wrap">
          MedReturn · SIH 2026 prototype ·{' '}
          <Link to="/safety" style={{ color: 'var(--teal)' }}>
            Safety and limitations
          </Link>
        </div>
      </footer>
    </>
  )
}
