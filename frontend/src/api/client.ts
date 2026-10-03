const BASE = '/api'

import { enqueueOutbox, isOffline } from './outbox'

const TOKEN_STORE = typeof window !== 'undefined' ? window.sessionStorage : null

let _token: string | null = TOKEN_STORE?.getItem('token') ?? null
let _refreshToken: string | null = TOKEN_STORE?.getItem('refresh_token') ?? null
let _isRefreshing = false

export function setToken(t: string | null) {
  _token = t
  if (t) TOKEN_STORE?.setItem('token', t)
  else TOKEN_STORE?.removeItem('token')
}

export function setRefreshToken(t: string | null) {
  _refreshToken = t
  if (t) TOKEN_STORE?.setItem('refresh_token', t)
  else TOKEN_STORE?.removeItem('refresh_token')
}

export function getToken() {
  return _token
}

// True when the fetch failure was a network problem (server unreachable /
// laptop asleep / tunnel down), NOT an HTTP error response. request() only
// throws Error(data.detail) for HTTP errors, so a TypeError here means the
// fetch itself failed — the offline case. The service worker additionally
// returns 503 {"offline":true,"error":"You are offline"} for API calls when
// offline, which surfaces here as Error('You are offline').
export function isNetworkError(err: unknown): boolean {
  if (isOffline()) return true
  if (err instanceof TypeError) return true
  if (err instanceof Error) {
    if (err.message === 'fetch failed') return true
    if (err.message === 'You are offline' || err.message.includes('offline')) return true
  }
  return false
}

async function tryRefresh(): Promise<boolean> {
  if (!_refreshToken || _isRefreshing) return false
  _isRefreshing = true
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    })
    if (res.ok) {
      const data = await res.json()
      setToken(data.access_token)
      if (data.refresh_token) setRefreshToken(data.refresh_token)
      _isRefreshing = false
      return true
    }
    setToken(null)
    setRefreshToken(null)
    _isRefreshing = false
    return false
  } catch {
    _isRefreshing = false
    return false
  }
}

// Retry transient failures so a free-tier cold-start blip (502/503/504 or a
// dropped connection) self-heals instead of surfacing as an error. Reads are
// always retried; writes are retried only on network-level failures (when the
// server likely never received the request), never on HTTP errors.
const RETRYABLE_STATUS = new Set([502, 503, 504])
const MAX_ATTEMPTS = 3

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function fetchWithRetry(url: string, init: RequestInit, method: string): Promise<Response> {
  let lastErr: unknown = null
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    let res: Response
    try {
      res = await fetch(url, init)
    } catch (err) {
      lastErr = err
      const retryNetwork = isNetworkError(err) && (method === 'GET' || method === 'HEAD')
      if (attempt < MAX_ATTEMPTS && retryNetwork) {
        await delay(500 * attempt)
        continue
      }
      throw err
    }
    const retryHttp = res && RETRYABLE_STATUS.has(res.status) && method === 'GET'
    if (attempt < MAX_ATTEMPTS && retryHttp) {
      await delay(500 * attempt)
      continue
    }
    return res
  }
  throw lastErr ?? new Error('Request failed after retries')
}

async function request(path: string, options: RequestInit = {}, isRetry = false): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const method = options.method || 'GET'
  const res = await fetchWithRetry(`${BASE}${path}`, { ...options, headers }, method)

  if (res.status === 401 && !isRetry && path !== '/auth/refresh') {
    const refreshed = await tryRefresh()
    if (refreshed) return request(path, options, true)
    setToken(null)
    setRefreshToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  let data: any = {}
  try {
    const text = await res.text()
    try { data = JSON.parse(text) } catch { data = { detail: text || 'Request failed' } }
  } catch { data = { detail: 'Request failed' } }
  if (!res.ok) throw new Error(data.detail || data.message || 'Request failed')
  if (data?.success === true && data?.data !== undefined) return data.data
  return data
}

function buildBody(data: any): string | undefined {
  if (data === undefined || data === null) return undefined
  if (typeof data === 'string') return data
  return JSON.stringify(data)
}

// Multipart upload that goes through the same auth/refresh path as request()
// but without forcing a JSON Content-Type (the browser sets the boundary).
async function upload(path: string, file: File, isRetry = false): Promise<any> {
  const headers: Record<string, string> = {}
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const body = new FormData()
  body.append('file', file)

  const res = await fetch(`${BASE}${path}`, { method: 'POST', headers, body })

  if (res.status === 401 && !isRetry && path !== '/auth/refresh') {
    const refreshed = await tryRefresh()
    if (refreshed) return upload(path, file, true)
    setToken(null)
    setRefreshToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  let data: any = {}
  try {
    const text = await res.text()
    try { data = JSON.parse(text) } catch { data = { detail: text || 'Request failed' } }
  } catch { data = { detail: 'Request failed' } }
  if (!res.ok) throw new Error(data.detail || data.message || 'Request failed')
  if (data?.success === true && data?.data !== undefined) return data.data
  return data
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, data?: any) => request(path, { method: 'POST', body: buildBody(data) }),
  put: (path: string, data?: any) => request(path, { method: 'PUT', body: buildBody(data) }),
  delete: (path: string) => request(path, { method: 'DELETE' }),

  // Auth
  login: (username: string, password: string) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (data: any) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  unlock: (passphrase: string) =>
    request('/auth/unlock', { method: 'POST', body: JSON.stringify({ passphrase }) }),
  encryptionStatus: () => request('/auth/encryption-status'),
  verifyEmail: (token: string) => request(`/auth/verify-email?token=${encodeURIComponent(token)}`),
  resendVerification: (username: string) =>
    request('/auth/resend-verification', { method: 'POST', body: JSON.stringify({ username }) }),

  // Admin invites (doctor signup codes)
  listInvites: () => request('/admin/invites'),
  createInvite: (data: { clinic_code: string; max_uses?: number; expires_in_days?: number }) =>
    request('/admin/invites', { method: 'POST', body: JSON.stringify(data) }),
  revokeInvite: (code: string) => request(`/admin/invites/${encodeURIComponent(code)}`, { method: 'DELETE' }),

  // Doctor creates a client account in-clinic
  createClientAccount: (data: any) => request('/patients/create-client', { method: 'POST', body: JSON.stringify(data) }),

  // Patients
  getMe: () => request('/patients/me'),
  updateContact: (data: any) => request('/patients/me/contact', { method: 'PUT', body: JSON.stringify(data) }),
  updatePreferences: (data: any) => request('/patients/me/preferences', { method: 'PUT', body: JSON.stringify(data) }),
  getPatientProfile: (username: string) => request(`/patients/${username}/profile`),
  getPatientSummary: (username: string) => request(`/patients/${username}/summary`),
  getPatientOverview: (username: string) => request(`/patients/${username}/overview`),
  getStressSpikes: (username: string, days: number = 30) => request(`/physio/stress-spikes/${username}?days=${days}`),
  getPlainInsights: (username: string) => request(`/patients/${username}/plain-insights`),
  uploadConsentForm: (file: File) => upload('/patients/me/consent', file),
  getWellness: () => request('/patients/me/wellness'),
  updateOnboarding: (step: number) => request('/patients/me/onboarding', { method: 'PUT', body: JSON.stringify({ step }) }),
  assignPsychologist: (username: string, psychUsername: string) =>
    request(`/patients/${username}/assign-psych`, { method: 'POST', body: JSON.stringify({ psych_username: psychUsername }) }),

  // Psychologists
  getPsychPatients: () => request('/psychologists/patients'),
  getCaseloadHealth: () => request('/psychologists/caseload-health'),
  getAvailablePsychs: (clinic?: string) => request(`/psychologists/available${clinic ? `?clinic=${clinic}` : ''}`),
  getPsychNotes: (filters?: { patient?: string; q?: string; date_from?: string; date_to?: string; approved?: string }) => {
    const p = new URLSearchParams()
    if (filters?.patient) p.set('patient', filters.patient)
    if (filters?.q) p.set('q', filters.q)
    if (filters?.date_from) p.set('date_from', filters.date_from)
    if (filters?.date_to) p.set('date_to', filters.date_to)
    if (filters?.approved) p.set('approved', filters.approved)
    const qs = p.toString()
    return request(`/psychologists/notes${qs ? `?${qs}` : ''}`)
  },
  createPsychNote: (data: any) => request('/psychologists/notes', { method: 'POST', body: JSON.stringify(data) }),
  updatePsychNote: (id: number, data: { raw_notes: string }) => request(`/psychologists/notes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Session reports (clinician one-page reports)
  getReports: (patient: string) => request(`/session-reports?patient=${encodeURIComponent(patient)}`),
  getReport: (id: number) => request(`/session-reports/${id}`),
  createReport: (data: any) => request('/session-reports', { method: 'POST', body: JSON.stringify(data) }),
  updateReport: (id: number, data: any) => request(`/session-reports/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteReport: (id: number) => request(`/session-reports/${id}`, { method: 'DELETE' }),
  approveReport: (id: number) => request(`/session-reports/${id}/approve`, { method: 'PUT' }),
  uploadReportFile: (id: number, file: File) => upload(`/session-reports/${id}/upload`, file),
  getReportAttachmentUrl: (id: number) => `${BASE}/session-reports/${id}/attachment`,
  downloadReportExport: (id: number, filename: string) => api.downloadExport(`/session-reports/${id}/export`, filename),
  downloadReportAttachment: (id: number, filename: string) => api.downloadExport(`/session-reports/${id}/attachment`, filename),

  // Journal
  getJournalPrompts: () => request('/journal/prompts'),
  async createJournal(raw: string, checkin?: { question: string; answer: string }[]) {
    const body = { raw_content: raw, timestamp: new Date().toISOString(), checkin: checkin || [] }
    try {
      return await request('/journal', { method: 'POST', body: JSON.stringify(body) })
    } catch (err) {
      if (isNetworkError(err)) {
        return { queued: true, offline: true, client_id: await enqueueOutbox('journal', { raw_content: raw, timestamp: new Date().toISOString() }) }
      }
      throw err
    }
  },
  getJournals: (filters?: { emotion?: string; ai_source?: string; date_from?: string; date_to?: string }) => {
    const p = new URLSearchParams()
    if (filters?.emotion) p.set('emotion', filters.emotion)
    if (filters?.ai_source) p.set('ai_source', filters.ai_source)
    if (filters?.date_from) p.set('date_from', filters.date_from)
    if (filters?.date_to) p.set('date_to', filters.date_to)
    const qs = p.toString()
    return request(`/journal${qs ? `?${qs}` : ''}`)
  },
  getPatientJournals: (username: string) => request(`/journal/${username}`),
  getPatientSummaries: (username: string) => request(`/journal/${username}/summaries`),
  resummarizeJournal: (journalId: number) => request(`/journal/${journalId}/resummarize`, { method: 'POST' }),
  synthesizeNote: (journalText: string, clinicalSummary?: string) =>
    request('/journal/synthesize-note', { method: 'POST', body: JSON.stringify({ journal_text: journalText, clinical_summary: clinicalSummary || '' }) }),

  // Mood
  async logMood(date: string, emoji: string, label: string) {
    try {
      return await request('/mood', { method: 'POST', body: JSON.stringify({ date, emoji, label }) })
    } catch (err) {
      if (isNetworkError(err)) {
        return { queued: true, offline: true, client_id: await enqueueOutbox('mood', { date, emoji, label, timestamp: new Date().toISOString() }) }
      }
      throw err
    }
  },
  getMoods: () => request('/mood'),
  getPatientMoods: (username: string) => request(`/mood/${username}`),
  checkTodayMood: () => request('/mood/today/check'),
  getStreaks: () => request('/patients/me/streaks'),

  // Crisis
  getCrisisState: () => request('/crisis/state'),
  triggerCrisis: () => request('/crisis/trigger', { method: 'POST' }),
  acknowledgeCrisis: () => request('/crisis/acknowledge', { method: 'POST' }),
  resolveCrisis: () => request('/crisis/resolve', { method: 'POST' }),
  assessRisk: (text: string) => request('/crisis/assess-risk', { method: 'POST', body: JSON.stringify({ text }) }),
  getCrisisElapsed: () => request('/crisis/elapsed'),
  getCrisisHistory: (username: string) => request(`/crisis/history/${username}`),
  notifyTrustedContact: () => request('/crisis/notify-trusted-contact', { method: 'POST' }),
  trusteeAcknowledge: () => request('/crisis/trustee-acknowledge', { method: 'POST' }),
  trusteeClicked: () => request('/crisis/trustee-clicked', { method: 'POST' }),

  // Coping Toolbox
  getCopingTools: () => request('/coping-tools'),
  createCopingTool: (data: { title: string; description?: string; category?: string }) =>
    request('/coping-tools', { method: 'POST', body: JSON.stringify(data) }),
  updateCopingTool: (id: number, data: any) => request(`/coping-tools/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCopingTool: (id: number) => request(`/coping-tools/${id}`, { method: 'DELETE' }),
  recommendCopingTool: (data: { patient_username: string; title: string; description?: string; category?: string }) =>
    request('/coping-tools/recommend', { method: 'POST', body: JSON.stringify(data) }),
  getPatientCopingTools: (username: string) => request(`/coping-tools/patient/${username}`),
  getSessionReadiness: (username: string) => request(`/agents/session-readiness/${username}`),
  getWeeklyDigest: () => request('/agents/weekly-digest'),
  getReflectPrompt: () => request('/agents/reflect-prompt'),
  getWeeklyTheme: (username: string) => request(`/agents/weekly-theme/${username}`),
  getNextSessionPrep: (username: string) => request(`/agents/next-session-prep/${username}`),
  getMoodForecast: () => request('/agents/mood-forecast'),
  getJournalReframe: (entryId: number) => request(`/agents/journal-reframe/${entryId}`),
  getEarlyWarning: (username: string) => request(`/agents/early-warning/${username}`),
  getGoalSuggestions: () => request('/agents/goal-suggestions'),

  // Bookings
  createBooking: (data: any) => request('/bookings', { method: 'POST', body: JSON.stringify(data) }),
  getBookings: (filters?: { status?: string; upcoming?: boolean; past?: boolean; date_from?: string; date_to?: string }) => {
    const p = new URLSearchParams()
    if (filters?.status) p.set('status', filters.status)
    if (filters?.upcoming) p.set('upcoming', 'true')
    if (filters?.past) p.set('past', 'true')
    if (filters?.date_from) p.set('date_from', filters.date_from)
    if (filters?.date_to) p.set('date_to', filters.date_to)
    const qs = p.toString()
    return request(`/bookings${qs ? `?${qs}` : ''}`)
  },
  updateBookingStatus: (id: number, status: string) =>
    request(`/bookings/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),
  setAvailability: (data: any) => request('/bookings/availability', { method: 'POST', body: JSON.stringify(data) }),
  getBookingCalendar: (year: number, month: number) => request(`/bookings/calendar?year=${year}&month=${month}`),
  getNextFreeSlots: (psychUsername: string, count: number = 3) => request(`/bookings/next-free/${psychUsername}?count=${count}`),
  getWeekSummary: () => request('/patients/me/week-summary'),
  getMyAvailability: (detailed?: boolean) => request(`/bookings/availability/me${detailed ? '?detailed=true' : ''}`),
  rescheduleBooking: (id: number, date: string, time: string) =>
    request(`/bookings/${id}/reschedule`, { method: 'PUT', body: JSON.stringify({ date, time }) }),
  deleteAvailability: (slotId: number) => request(`/bookings/availability/${slotId}`, { method: 'DELETE' }),

  // Followup templates
  getFollowupTemplates: (category?: string) => request(`/followup-templates${category ? `?category=${category}` : ''}`),
  createFollowupTemplate: (data: { title: string; description?: string; category?: string; default_due_days?: number }) =>
    request('/followup-templates', { method: 'POST', body: JSON.stringify(data) }),
  updateFollowupTemplate: (id: number, data: any) => request(`/followup-templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFollowupTemplate: (id: number) => request(`/followup-templates/${id}`, { method: 'DELETE' }),
  assignFromTemplate: (id: number, patientUsername: string, dueDate?: string) =>
    request(`/followup-templates/${id}/assign`, { method: 'POST', body: JSON.stringify({ patient_username: patientUsername, due_date: dueDate || '' }) }),

  // Followups
  createFollowup: (data: any) => request('/followups', { method: 'POST', body: JSON.stringify(data) }),
  getFollowups: (filters?: { status?: string; patient?: string; overdue?: boolean; due_before?: string }) => {
    const p = new URLSearchParams()
    if (filters?.status) p.set('status', filters.status)
    if (filters?.patient) p.set('patient', filters.patient)
    if (filters?.overdue) p.set('overdue', 'true')
    if (filters?.due_before) p.set('due_before', filters.due_before)
    const qs = p.toString()
    return request(`/followups${qs ? `?${qs}` : ''}`)
  },
  getFollowupStats: () => request('/followups/stats'),
  updateFollowup: (id: string, data: any) => request(`/followups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  uploadFollowupAttachment: (id: string, file: File) => upload(`/followups/${id}/upload`, file),
  uploadFollowupProof: (id: string, file: File) => upload(`/followups/${id}/upload-proof`, file),

  // Ring
  pushSensorData: (data: any) => request('/ring/data', { method: 'POST', body: JSON.stringify(data) }),
  getSensorData: () => request('/ring/data'),

  // Timeline
  getTimeline: (username: string, days: number = 30) => request(`/timeline/${username}?days=${days}`),
  getMetrics: (username: string) => request(`/timeline/${username}/metrics`),

  // Agents
  triageSummary: (patientUsername: string) =>
    request('/agents/triage-summary', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  suggestSlots: (patientUsername: string) =>
    request('/agents/suggest-slots', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  draftFollowup: (patientUsername: string) =>
    request('/agents/draft-followup', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  journalToNote: (patientUsername: string, journalText: string, clinicalSummary?: string) =>
    request('/agents/journal-to-note', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername, journal_text: journalText, clinical_summary: clinicalSummary || '' }) }),
  preSessionBrief: (patientUsername: string) =>
    request('/agents/pre-session-brief', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  complianceRadar: () => request('/agents/compliance-radar', { method: 'POST' }),
  silentPeriodWatch: () => request('/agents/silent-period-watch', { method: 'POST' }),
  relapseIndicators: () => request('/agents/relapse-indicators', { method: 'POST' }),
  crossPatientPatterns: () => request('/agents/cross-patient-patterns', { method: 'POST' }),
  ringVitalsRisk: () => request('/agents/ring-vitals-risk', { method: 'POST' }),

  // Triage
  createTriage: (patientUsername: string) =>
    request('/triage', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  getTriage: () => request('/triage'),
  getPatientTriage: (patientUsername: string) => request(`/triage/${patientUsername}`),
  updateTriage: (entryId: string, data: any) => request(`/triage/${entryId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Emotions (timeline)
  getEmotionTimeline: (username: string, days: number = 30) => request(`/emotions/timeline/${username}?days=${days}`),
  getEmotionSummary: (username: string, days: number = 30) => request(`/emotions/summary/${username}?days=${days}`),

  // Event Store
  getEvents: (eventType?: string, limit: number = 50) => request(`/events?limit=${limit}${eventType ? `&event_type=${eventType}` : ''}`),
  getPatientEvents: (username: string, limit: number = 50) => request(`/events/patient/${username}?limit=${limit}`),
  replayEvents: (fromSequence: number = 0) => request(`/events/replay?from_sequence=${fromSequence}`),

  // ML Registry
  getMLModels: () => request('/ml/models'),
  getMLModel: (name: string) => request(`/ml/models/${name}`),
  getFeatureStoreStats: () => request('/ml/feature-store/stats'),

  // Psych Journal
  createPsychJournal: (raw: string) => request('/psych-journal', { method: 'POST', body: JSON.stringify({ raw_content: raw }) }),
  getPsychJournals: () => request('/psych-journal'),

  // Activity
  getActivityFeed: (days?: number) => request(`/activity?days=${days || 7}`),

  // Emotion Results (structured table)
  getEmotionResultByJournal: (journalId: number) => request(`/emotion-results/journal/${journalId}`),
  getEmotionResultsForPatient: (username: string) => request(`/emotion-results/patient/${username}`),

  // AI Analyses (structured table)
  getAIAnalysisByJournal: (journalId: number) => request(`/ai-analyses/journal/${journalId}`),
  getAIAnalysesForPatient: (username: string) => request(`/ai-analyses/patient/${username}`),

  // Sensor Readings (structured table)
  createSensorReading: (data: any) => request('/sensor-readings', { method: 'POST', body: JSON.stringify(data) }),
  getSensorReadings: () => request('/sensor-readings'),
  getPatientSensorReadings: (username: string) => request(`/sensor-readings/patient/${username}`),

  // Risk Assessments (structured table)
  getRiskAssessmentByJournal: (journalId: number) => request(`/risk-assessments/journal/${journalId}`),
  getRiskAssessmentsForPatient: (username: string) => request(`/risk-assessments/patient/${username}`),

  // Notifications
  getNotifications: () => request('/notifications'),
  getUnreadNotifications: () => request('/notifications/unread'),
  markNotificationRead: (id: number) => request(`/notifications/${id}/read`, { method: 'PUT', body: JSON.stringify({ read: true }) }),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'PUT' }),

  // Search
  searchJournals: (query: string, patientUsername?: string) =>
    request(`/search/journals?q=${encodeURIComponent(query)}${patientUsername ? `&patient_username=${patientUsername}` : ''}`),

  // Offline Sync
  syncOfflineJournals: (entries: any[]) => request('/sync/journals', { method: 'POST', body: JSON.stringify(entries) }),
  syncOfflineMoods: (entries: any[]) => request('/sync/moods', { method: 'POST', body: JSON.stringify(entries) }),

  // Feature Flags
  getFeatureFlags: () => request('/feature-flags'),
  updateFeatureFlag: (name: string, enabled: boolean, rolloutPct: number = 100) =>
    request(`/feature-flags/${name}?enabled=${enabled}&rollout_pct=${rolloutPct}`, { method: 'PUT' }),

  // Export
  // Auth goes in the Authorization header (never in the URL), token stays out of
  // browser history / server logs. Returns the download URL for the client to open.
  async downloadExport(path: string, filename: string): Promise<string> {
    if (!_token) throw new Error('Unauthorized')
    const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${_token}` } })
    if (res.status === 401) {
      setToken(null)
      setRefreshToken(null)
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Download failed')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    return url
  },
  exportJournalSummaries: (days: number = 30) => api.downloadExport(`/export/journal-summaries?days=${days}`, 'sentinel_journal_summaries.csv'),
  exportClinicalNotes: (days: number = 30) => api.downloadExport(`/export/clinical-notes?days=${days}`, 'sentinel_clinical_notes.csv'),
  exportPatientData: () => api.downloadExport('/export/patient-data', 'sentinel_patient_data.csv'),
}
