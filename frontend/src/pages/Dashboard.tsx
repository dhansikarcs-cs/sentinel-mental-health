import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import RingConnect from '../components/RingConnect'
import RingVitalsCard from '../components/RingVitalsCard'
import { getUser } from '../stores/auth'

export default function Dashboard() {
  const [wellness, setWellness] = useState<any>(null)
  const [comparison, setComparison] = useState<any>(null)
  const [showComparison, setShowComparison] = useState(false)

  const refresh = useCallback(() => {
    api.getWellness().then(setWellness).catch(() => {})
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function runComparison() {
    const user = getUser()
    if (!user?.username) return
    setShowComparison(true)
    try {
      setComparison(await api.checkPatientDiscrepancy(user.username))
    } catch (e) {
      setComparison({ error: e instanceof Error ? e.message : String(e) })
    }
  }

  return (
    <div className="animate-fade-in space-y-4">
      <h2>📊 Wellness Dashboard</h2>

      <RingConnect onSynced={refresh} />

      <div className="card" style={{ padding: '20px' }} data-tour="dashboard">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Today's Mood</div>
            <div style={{ fontSize: '2rem' }}>{wellness?.mood?.emoji || '\u{1F610}'}</div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)' }}>{wellness?.mood?.label || 'Not logged'}</div>
          </div>
          <div style={{ width: '1px', height: '40px', background: 'var(--border)' }} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Journal Activity</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--heading)' }}>{wellness?.journals_today || 0}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>entries today</div>
          </div>
        </div>
      </div>

      {/* Always visible: an account with no ring rows shows dashes + a
          "connect your ring" message, never a blank/broken-looking page. */}
      <RingVitalsCard data={wellness} />

      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)', fontWeight: 600 }}>🧠 Journal ↔ Vitals Comparison</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px', lineHeight: 1.5 }}>
              Compares your last journal's sentiment with your real wearable readings. Uses stored data only — nothing typed or estimated.
            </div>
          </div>
          <button className="btn-secondary" onClick={runComparison} style={{ padding: '9px 16px', fontSize: '0.8125rem' }}>
            Compare
          </button>
        </div>
        {showComparison && comparison && (
          <div style={{ marginTop: '10px', fontSize: '0.72rem', lineHeight: 1.6 }}>
            {comparison.error ? (
              <span style={{ color: 'var(--danger)' }}>{comparison.error}</span>
            ) : !comparison.vitals_available || !comparison.journal_available ? (
              <span style={{ color: 'var(--muted)' }}>
                Insufficient real data — needs a journal entry and measured bpm + hrv. Nothing is estimated.
              </span>
            ) : (
              <span>
                Sentiment <strong>{comparison.text_sentiment}</strong> · biometrics{' '}
                <strong>{comparison.biometric_state}</strong> (bpm {comparison.bpm}, hrv {comparison.hrv}) ·{' '}
                <strong style={{ color: comparison.discrepancy_detected ? 'var(--danger)' : 'var(--ok)' }}>
                  {comparison.discrepancy_detected ? 'mismatch flagged' : 'no mismatch'}
                </strong>
              </span>
            )}
          </div>
        )}
      </div>

      {wellness?.mood_trend && wellness.mood_trend.length > 0 && (
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '12px' }}>Mood Trend (7 days)</div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {wellness.mood_trend.map((m: any, i: number) => (
              <div key={i} style={{ textAlign: 'center', padding: '8px', background: 'var(--surface)', borderRadius: '8px', minWidth: '60px' }}>
                <div style={{ fontSize: '1.5rem' }}>{m.emoji}</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--muted)', marginTop: '2px' }}>{m.date?.slice(-2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {wellness?.ai_insights && (
        <div className="expander">
          <details>
            <summary className="expander-header">📊 My Insights (AI-Powered)</summary>
            <div className="expander-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>📝 Journals (7d)</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.journal_count || 0}</div>
                </div>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>✅ Compliance</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.compliance || 0}%</div>
                </div>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>❌ Missed</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.missed || 0}</div>
                </div>
              </div>
              {wellness.ai_insights.grades && (
                <div style={{ color: 'var(--muted)', fontSize: '0.75rem', marginBottom: '8px' }}>
                  Grades: 🟢{wellness.ai_insights.grades.green || 0}  🟡{wellness.ai_insights.grades.yellow || 0}  🔴{wellness.ai_insights.grades.red || 0}
                </div>
              )}
              {wellness.ai_insights.mood_message && (
                <div style={{ color: 'var(--secondary)', fontSize: '0.8125rem', marginBottom: '4px' }}>{wellness.ai_insights.mood_message}</div>
              )}
              <div style={{ marginTop: '6px', color: 'var(--muted)', fontSize: '0.65rem', lineHeight: 1.5 }}>
                AI-generated insights, not reviewed by your psychologist. Sentinel assists monitoring — it never determines whether you are safe. If you feel unsafe, seek help immediately.
              </div>
              {wellness.ai_insights.relapse_flag && (
                <div className="card" style={{ borderColor: 'rgba(199,70,59,0.4)', color: 'var(--danger)', fontSize: '0.8125rem' }}>
                  ⚠️ {wellness.ai_insights.relapse_message || 'Warning flagged'}
                </div>
              )}
            </div>
          </details>
        </div>
      )}
    </div>
  )
}
