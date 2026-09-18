/** Small presentational primitives shared across pages. */

import { stagePillClass, STAGE_LABEL } from '../lib/format'

export const Card = ({ children, className = '', ...rest }) => (
  <div className={`card ${className}`} {...rest}>{children}</div>
)

export const Pill = ({ tone = 'grey', children }) => (
  <span className={`pill p-${tone}`}>{children}</span>
)

export const StagePill = ({ status }) => (
  <span className={`pill ${stagePillClass(status)}`}>
    {STAGE_LABEL[status] || status}
  </span>
)

export const DemoTag = ({ children = 'DEMO MODE' }) => (
  <span className="demo">{children}</span>
)

export const Stat = ({ value, label, color }) => (
  <div className="card stat">
    <div className="v" style={color ? { color } : undefined}>{value}</div>
    <div className="k">{label}</div>
  </div>
)

export const PageHeader = ({ title, subtitle, actions }) => (
  <div className="ph between">
    <div>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
    {actions}
  </div>
)

export const Loading = ({ label = 'Loading…' }) => (
  <div className="loading"><div className="spin" />{label}</div>
)

export const ErrorNote = ({ error }) =>
  !error ? null : (
    <div className="err">
      {error.message}
      {error.problems?.length > 0 && (
        <ul style={{ margin: '6px 0 0 16px', padding: 0 }}>
          {error.problems.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}
    </div>
  )

export const Empty = ({ title, children, action }) => (
  <div className="empty">
    {title && <h3>{title}</h3>}
    {children && <p>{children}</p>}
    {action}
  </div>
)

export const KV = ({ label, children }) => (
  <div className="kv"><span>{label}</span><span>{children}</span></div>
)

export const ConfidencePill = ({ value, threshold = 0.8 }) => {
  const tone = value >= threshold ? 'green' : value >= 0.6 ? 'amber' : 'red'
  return <span className={`pill p-${tone} mono`}>{Math.round(value * 100)}%</span>
}
