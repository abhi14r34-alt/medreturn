/** Shared formatting helpers. */

export const STAGES = [
  ['REQUESTED', 'Pickup requested'],
  ['SCHEDULED', 'Pickup scheduled'],
  ['ASSIGNED', 'Collector assigned'],
  ['ON_THE_WAY', 'Pickup on the way'],
  ['ARRIVED', 'Collector arrived'],
  ['COLLECTED', 'Items collected'],
  ['VERIFIED', 'Items verified'],
  ['CREDITS_AWARDED', 'Credits awarded'],
  ['COMPLETED', 'Completed'],
]

export const STAGE_LABEL = Object.fromEntries(STAGES)
export const stageIndex = (s) => STAGES.findIndex(([k]) => k === s)

export function formatDate(value, withTime = false) {
  if (!value) return '—'
  const d = new Date(value)
  const date = d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
  if (!withTime) return date
  return `${date}, ${d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`
}

export function timeAgo(value) {
  const minutes = Math.floor((Date.now() - new Date(value)) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export const percent = (v) => `${Math.round((v || 0) * 100)}%`

export function stagePillClass(status) {
  if (['VERIFIED', 'CREDITS_AWARDED', 'COMPLETED'].includes(status)) return 'p-green'
  if (['ON_THE_WAY', 'ARRIVED', 'COLLECTED'].includes(status)) return 'p-teal'
  if (['SCHEDULED', 'ASSIGNED'].includes(status)) return 'p-blue'
  if (status === 'CANCELLED') return 'p-red'
  return 'p-grey'
}

export const todayISO = () => new Date().toISOString().slice(0, 10)
