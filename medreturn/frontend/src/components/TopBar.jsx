import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import { HOME_FOR_ROLE, useAuth } from '../lib/auth.jsx'

const PUBLIC_LINKS = [
  ['How it works', '/how-it-works'],
  ['About', '/about'],
  ['Safety', '/safety'],
  ['Contact', '/contact'],
]

export default function TopBar() {
  const { user, logout } = useAuth()
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('medreturn.theme')
    return saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('medreturn.theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme((current) => current === 'dark' ? 'light' : 'dark')

  return (
    <header className="top">
      <div className="in">
        <Link className="brand" to="/">
          <span className="mark">M</span>MedReturn
        </Link>
        <nav className="nav">
          {PUBLIC_LINKS.map(([label, path]) => (
            <NavLink key={path} to={path} className={({ isActive }) => (isActive ? 'on' : '')}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <button
          className="btn sm theme-toggle"
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          <span className="hidemob">{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
        {user ? (
          <>
            <span className="pill p-grey whoami">{user.full_name} · {user.role}</span>
            <Link className="btn sm hidemob" to={HOME_FOR_ROLE[user.role] || '/'}>
              Dashboard
            </Link>
            <button className="btn sm ghost" onClick={logout}>Sign out</button>
          </>
        ) : (
          <>
            <Link className="btn sm ghost" to="/login">Log in</Link>
            <Link className="btn sm pri" to="/register">Create account</Link>
          </>
        )}
      </div>
    </header>
  )
}
