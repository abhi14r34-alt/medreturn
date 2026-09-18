import { STAGES, stageIndex, formatDate } from '../lib/format'

/** Visual pickup lifecycle. History rows add timestamps where we have them. */
export default function Timeline({ status, history = [] }) {
  const current = stageIndex(status)

  return (
    <ul className="tl">
      {STAGES.map(([key, label], index) => {
        const state = index < current ? 'done' : index === current ? 'cur' : ''
        const entry = history.find((h) => h.status === key)
        return (
          <li key={key} className={state}>
            <span className="dot">{index < current ? '✓' : index === current ? '●' : ''}</span>
            <div>
              <div className="t">{label}</div>
              {entry && <div className="s">{formatDate(entry.created_at, true)}</div>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
