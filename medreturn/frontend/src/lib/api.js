/**
 * Single place that talks to the FastAPI backend.
 *
 * The JWT lives in localStorage and is attached to every request. A 401
 * clears it and bounces the user to the login screen, so an expired token
 * never leaves the UI in a half-authenticated state.
 */

const BASE = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'medreturn.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  constructor(message, status, problems) {
    super(message)
    this.status = status
    this.problems = problems || []
  }
}

async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(
      'Cannot reach the MedReturn server. Check that the backend is running.',
      0,
    )
  }

  if (response.status === 401) {
    clearToken()
    if (!location.hash.includes('/login')) location.hash = '#/login'
    throw new ApiError('Your session expired. Please sign in again.', 401)
  }

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const detail =
      payload?.detail || `Request failed (${response.status}). Please try again.`
    throw new ApiError(detail, response.status, payload?.problems)
  }
  return payload
}

export const api = {
  // auth
  register: (data) => request('/auth/register', { method: 'POST', body: data }),
  login: (data) => request('/auth/login', { method: 'POST', body: data }),
  me: () => request('/auth/me'),
  updateProfile: (data) => request('/auth/me', { method: 'PATCH', body: data }),

  // household
  analyze: (file, fields = {}) => {
    const form = new FormData()
    form.append('file', file)
    Object.entries(fields).forEach(([key, value]) => {
      if (value) form.append(key, value)
    })
    return request('/household/analyze', { method: 'POST', body: form, isForm: true })
  },
  createPickup: (data) => request('/household/pickups', { method: 'POST', body: data }),
  myPickups: () => request('/household/pickups'),
  pickup: (id) => request(`/household/pickups/${id}`),
  tracking: (id) => request(`/household/pickups/${id}/tracking`),
  cancelPickup: (id) => request(`/household/pickups/${id}/cancel`, { method: 'POST' }),
  credits: () => request('/household/credits'),
  creditTransactions: () => request('/household/credits/transactions'),
  returnHistory: () => request('/household/history'),

  // hospital
  predictWaste: (file, weightKg, location, fields = {}) => {
    const form = new FormData()
    form.append('file', file)
    form.append('weight_kg', String(weightKg))
    form.append('location', location)
    Object.entries(fields).forEach(([key, value]) => {
      if (value) form.append(key, value)
    })
    return request('/hospital/predict', { method: 'POST', body: form, isForm: true })
  },
  hospitalDashboard: () => request('/hospital/dashboard'),
  wasteEvents: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null),
    ).toString()
    return request(`/hospital/events${query ? `?${query}` : ''}`)
  },
  bins: () => request('/hospital/bins'),
  quarantine: (openOnly = true) => request(`/hospital/quarantine?open_only=${openOnly}`),
  verifyQuarantine: (id, data) =>
    request(`/hospital/quarantine/${id}/verify`, { method: 'POST', body: data }),
  hospitalModel: () => request('/hospital/model'),

  // admin
  adminDashboard: () => request('/admin/dashboard'),
  adminPickups: (status) =>
    request(`/admin/pickups${status ? `?status_filter=${status}` : ''}`),
  updatePickupStatus: (id, data) =>
    request(`/admin/pickups/${id}/status`, { method: 'PATCH', body: data }),
  assignCollector: (id, collectorId) =>
    request(`/admin/pickups/${id}/assign`, {
      method: 'POST',
      body: { collector_id: collectorId },
    }),
  collectors: () => request('/admin/collectors'),
  users: () => request('/admin/users'),
  hospitals: () => request('/admin/hospitals'),
  allTransactions: () => request('/admin/credits/transactions'),
  emailLog: () => request('/admin/emails'),
  sendTestEmail: () => request('/admin/emails/test', { method: 'POST' }),
  adminModel: () => request('/admin/model'),
  adminSettings: () => request('/admin/settings'),

  // collector
  collectorPickups: () => request('/collector/pickups'),
  collectorCompleted: () => request('/collector/pickups/completed'),
  collectorStatus: (id, status) =>
    request(`/collector/pickups/${id}/status`, { method: 'PATCH', body: { status } }),

  // notifications
  notifications: () => request('/notifications'),
  unreadCount: () => request('/notifications/unread-count'),
  markRead: (id) => request(`/notifications/${id}/read`, { method: 'PATCH' }),
  markAllRead: () => request('/notifications/read-all', { method: 'PATCH' }),
}
