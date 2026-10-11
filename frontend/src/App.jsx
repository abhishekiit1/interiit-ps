import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const WS_URL = import.meta.env.VITE_WS_URL || (
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    : 'ws://localhost:3000/ws'
)

// ─── Hooks ────────────────────────────────────────────────────────────

function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([])
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setMessages((prev) => [data, ...prev].slice(0, 100))
        } catch (e) {
          // ignore non-JSON
        }
      }

      ws.onclose = () => {
        setConnected(false)
        reconnectTimerRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      reconnectTimerRef.current = setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) wsRef.current.close()
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    }
  }, [connect])

  return { connected, messages }
}

function useApi(endpoint, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refetch = useCallback(() => {
    setLoading(true)
    fetch(`${API_BASE}${endpoint}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => { setData(d); setError(null) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [endpoint])

  useEffect(() => {
    refetch()
  }, [refetch, ...deps])

  return { data, loading, error, refetch }
}

// ─── Components ───────────────────────────────────────────────────────

function Sidebar({ page, setPage, connected }) {
  const navItems = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'reports', icon: '📋', label: 'RCA Reports' },
    { id: 'alerts', icon: '🚨', label: 'Alert History' },
    { id: 'settings', icon: '⚙️', label: 'Settings' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">🔍</div>
          <div className="logo-text">
            <h1>RCA Agent</h1>
            <span>Root Cause Analysis</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${page === item.id ? 'active' : ''}`}
            onClick={() => setPage(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="connection-status">
          <span className={`status-dot ${connected ? 'connected' : ''}`} />
          {connected ? 'Live connected' : 'Disconnected'}
        </div>
      </div>
    </aside>
  )
}

function StatCard({ label, value, secondary, variant = 'blue' }) {
  return (
    <div className={`stat-card ${variant}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {secondary && <div className="stat-secondary">{secondary}</div>}
    </div>
  )
}

function Badge({ status }) {
  const icon = status === 'completed' ? '✓' : status === 'running' ? '⟳' : '✕'
  return <span className={`badge ${status}`}>{icon} {status}</span>
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const level = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="confidence-bar" style={{ width: 80 }}>
        <div className={`confidence-fill ${level}`} style={{ width: `${pct}%` }} />
      </div>
      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{pct}%</span>
    </div>
  )
}

// ─── Dashboard Page ───────────────────────────────────────────────────

function DashboardPage({ wsMessages, onNavigate }) {
  const { data: stats, loading } = useApi('/api/dashboard/stats')
  const { data: recentReports } = useApi('/api/reports?limit=5')
  const [showModal, setShowModal] = useState(false)
  const [incidentInput, setIncidentInput] = useState('')
  const [triggering, setTriggering] = useState(false)

  // Live alerts from WebSocket
  const liveAlerts = wsMessages.filter((m) => m.type === 'new_alert')

  const triggerInvestigation = async () => {
    if (!incidentInput.trim()) return
    setTriggering(true)
    try {
      const resp = await fetch(`${API_BASE}/api/investigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_description: incidentInput }),
      })
      if (resp.ok) {
        setIncidentInput('')
        setShowModal(false)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Dashboard</h2>
          <p>Real-time overview of your cluster investigations</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          🚀 Trigger Investigation
        </button>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <StatCard
          label="Total Investigations"
          value={loading ? '—' : stats?.total_reports || 0}
          secondary="All time"
          variant="blue"
        />
        <StatCard
          label="Completed"
          value={loading ? '—' : stats?.completed_reports || 0}
          secondary={`Avg confidence: ${stats?.avg_confidence || 0}%`}
          variant="green"
        />
        <StatCard
          label="Failed"
          value={loading ? '—' : stats?.failed_reports || 0}
          secondary="Need attention"
          variant="red"
        />
        <StatCard
          label="Alerts (24h)"
          value={loading ? '—' : stats?.recent_alerts_count || 0}
          secondary="From Prometheus"
          variant="amber"
        />
      </div>

      {/* Two-column layout */}
      <div className="two-col">
        {/* Live Alert Feed */}
        <div className="card">
          <div className="card-header">
            <h3>🔴 Live Alert Feed</h3>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {liveAlerts.length} alerts
            </span>
          </div>
          <div className="card-body-flush alert-feed">
            {liveAlerts.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 20px' }}>
                <div className="icon">📡</div>
                <h3>Listening for alerts...</h3>
                <p>Alerts from Prometheus AlertManager will appear here in real-time.</p>
              </div>
            ) : (
              liveAlerts.map((alert, i) => (
                <div key={i} className="alert-item">
                  <div className={`alert-severity ${alert.status || 'firing'}`} />
                  <div className="alert-content">
                    <div className="alert-title">{alert.alert_name}</div>
                    <div className="alert-desc">
                      {alert.pod_name} — {alert.description?.slice(0, 100)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Reports */}
        <div className="card">
          <div className="card-header">
            <h3>📋 Recent Investigations</h3>
            <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => onNavigate('reports')}>
              View All →
            </button>
          </div>
          <div className="card-body-flush">
            {!recentReports || recentReports.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 20px' }}>
                <div className="icon">🔍</div>
                <h3>No investigations yet</h3>
                <p>Trigger an investigation manually or wait for an alert.</p>
              </div>
            ) : (
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Status</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {recentReports.map((r) => (
                    <tr key={r.id} onClick={() => onNavigate('report-detail', r.id)}>
                      <td>{r.incident_description?.slice(0, 60)}...</td>
                      <td><Badge status={r.status} /></td>
                      <td><ConfidenceBar value={r.confidence} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Active Agent Steps */}
      {wsMessages.filter(m => m.type === 'agent_step').length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <h3>🤖 Live Agent Activity</h3>
            <div className="spinner" />
          </div>
          <div className="card-body">
            <div className="steps-timeline">
              {wsMessages
                .filter((m) => m.type === 'agent_step')
                .slice(0, 10)
                .map((step, i) => (
                  <div key={i} className="step-item">
                    <div className={`step-dot ${step.status}`} />
                    <div className="step-content">
                      <div className="step-node">{step.node_name}</div>
                      <div className="step-detail">{step.detail?.slice(0, 150)}</div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Trigger Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>🚀 Trigger Manual Investigation</h3>
            <p>Describe the incident to investigate. The agent will query Prometheus, Loki, and K8s automatically.</p>
            <div className="form-group">
              <label>Incident Description</label>
              <textarea
                className="form-input"
                rows={4}
                placeholder="e.g., The checkout service is experiencing 5xx errors and high latency"
                value={incidentInput}
                onChange={(e) => setIncidentInput(e.target.value)}
                style={{ resize: 'vertical' }}
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={triggerInvestigation} disabled={triggering}>
                {triggering ? <><div className="spinner" /> Starting...</> : '🔍 Start Investigation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Reports Page ─────────────────────────────────────────────────────

function ReportsPage({ onNavigate }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const endpoint = `/api/reports?limit=50${search ? `&search=${encodeURIComponent(search)}` : ''}${statusFilter ? `&status=${statusFilter}` : ''}`
  const { data: reports, loading, refetch } = useApi(endpoint, [search, statusFilter])

  const deleteReport = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this report?')) return
    await fetch(`${API_BASE}/api/reports/${id}`, { method: 'DELETE' })
    refetch()
  }

  return (
    <div>
      <div className="page-header">
        <h2>RCA Reports</h2>
        <p>All root cause analysis investigations</p>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <div className="search-bar" style={{ flex: 1 }}>
          <span>🔍</span>
          <input
            placeholder="Search incidents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="form-input"
          style={{ width: 160 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="card">
        <div className="card-body-flush" style={{ overflow: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
          {loading ? (
            <div className="empty-state">
              <div className="spinner" style={{ margin: '0 auto' }} />
            </div>
          ) : !reports || reports.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📋</div>
              <h3>No reports found</h3>
              <p>No investigations match your search criteria.</p>
            </div>
          ) : (
            <table className="report-table">
              <thead>
                <tr>
                  <th>Incident</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Duration</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} onClick={() => onNavigate('report-detail', r.id)}>
                    <td style={{ maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.incident_description}
                    </td>
                    <td>{new Date(r.created_at).toLocaleString()}</td>
                    <td><Badge status={r.status} /></td>
                    <td><ConfidenceBar value={r.confidence} /></td>
                    <td>{r.duration_seconds ? `${Math.round(r.duration_seconds)}s` : '—'}</td>
                    <td>
                      <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: 11 }} onClick={(e) => deleteReport(r.id, e)}>
                        🗑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Report Detail Page ───────────────────────────────────────────────

function ReportDetailPage({ reportId, onBack }) {
  const { data: report, loading } = useApi(`/api/reports/${reportId}`)
  const { data: steps } = useApi(`/api/reports/${reportId}/steps`)

  if (loading) return <div className="empty-state"><div className="spinner" style={{ margin: '0 auto' }} /></div>
  if (!report) return <div className="empty-state"><h3>Report not found</h3></div>

  return (
    <div className="report-detail">
      <button className="back-btn" onClick={onBack}>← Back to Reports</button>

      <div className="report-detail-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h2>Root Cause Analysis</h2>
          <Badge status={report.status} />
        </div>

        <div className="report-meta">
          <span className="report-meta-item"><strong>Generated:</strong> {new Date(report.created_at).toLocaleString()}</span>
          <span className="report-meta-item"><strong>Duration:</strong> {report.duration_seconds ? `${Math.round(report.duration_seconds)}s` : '—'}</span>
          <span className="report-meta-item"><strong>Confidence:</strong> {report.confidence_level} ({Math.round((report.confidence || 0) * 100)}%)</span>
        </div>
      </div>

      {/* Incident */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-body">
          <div className="report-section">
            <h4>🚨 Incident</h4>
            <p>{report.incident_description}</p>
          </div>
        </div>
      </div>

      {/* Root Cause */}
      {report.root_cause && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-body">
            <div className="report-section">
              <h4>🎯 Root Cause</h4>
              <div className="root-cause-highlight">{report.root_cause}</div>
            </div>
          </div>
        </div>
      )}

      <div className="two-col">
        {/* Evidence */}
        {report.evidence && report.evidence.length > 0 && (
          <div className="card">
            <div className="card-body">
              <div className="report-section">
                <h4>🔬 Evidence ({report.evidence.length} pieces)</h4>
                <ul>
                  {report.evidence.map((ev, i) => (
                    <li key={i}>{typeof ev === 'string' ? ev.slice(0, 200) : JSON.stringify(ev).slice(0, 200)}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Hypotheses */}
        {report.hypotheses && report.hypotheses.length > 0 && (
          <div className="card">
            <div className="card-body">
              <div className="report-section">
                <h4>💡 Hypotheses</h4>
                <ul>
                  {report.hypotheses.map((h, i) => (
                    <li key={i}>{h}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Corrective Actions */}
      {report.corrective_actions && report.corrective_actions.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-body">
            <div className="report-section">
              <h4>🛠️ Corrective Actions</h4>
              <ul>
                {report.corrective_actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Investigation Steps (Timeline) */}
      {steps && steps.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <h3>🔄 Investigation Timeline</h3>
          </div>
          <div className="card-body">
            <div className="steps-timeline">
              {steps.map((step, i) => (
                <div key={i} className="step-item">
                  <div className={`step-dot ${step.status === 'completed' || step.status === 'exit' ? 'completed' : step.status === 'failed' ? 'failed' : ''}`} />
                  <div className="step-content">
                    <div className="step-node">{step.node_name}</div>
                    <div className="step-detail">{step.detail}</div>
                    <div className="step-time">{new Date(step.timestamp).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {report.error_message && (
        <div className="card" style={{ marginTop: 24, borderColor: 'rgba(239, 68, 68, 0.3)' }}>
          <div className="card-body">
            <div className="report-section">
              <h4>❌ Error</h4>
              <p style={{ color: 'var(--accent-red)' }}>{report.error_message}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Alerts Page ──────────────────────────────────────────────────────

function AlertsPage() {
  const { data: alerts, loading } = useApi('/api/alerts?limit=100')

  return (
    <div>
      <div className="page-header">
        <h2>Alert History</h2>
        <p>All alerts received from Prometheus AlertManager</p>
      </div>

      <div className="card">
        <div className="card-body-flush" style={{ overflow: 'auto', maxHeight: 'calc(100vh - 220px)' }}>
          {loading ? (
            <div className="empty-state"><div className="spinner" style={{ margin: '0 auto' }} /></div>
          ) : !alerts || alerts.length === 0 ? (
            <div className="empty-state">
              <div className="icon">🚨</div>
              <h3>No alerts received yet</h3>
              <p>Alerts from Prometheus AlertManager will be logged here.</p>
            </div>
          ) : (
            <table className="report-table">
              <thead>
                <tr>
                  <th>Alert</th>
                  <th>Pod</th>
                  <th>Namespace</th>
                  <th>Status</th>
                  <th>Received</th>
                  <th>Investigation</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.alert_name}</td>
                    <td>{a.pod_name}</td>
                    <td>{a.namespace || '—'}</td>
                    <td>
                      <span className={`badge ${a.status === 'firing' ? 'failed' : 'completed'}`}>
                        {a.status}
                      </span>
                    </td>
                    <td>{new Date(a.received_at).toLocaleString()}</td>
                    <td>
                      {a.triggered_investigation ? (
                        <span style={{ fontSize: 12, color: 'var(--accent-blue)' }}>
                          {a.triggered_investigation.slice(0, 8)}...
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Settings Page ────────────────────────────────────────────────────

function SettingsPage() {
  const { data: config, loading } = useApi('/api/config')
  const { data: status } = useApi('/api/status')

  return (
    <div style={{ maxWidth: 700 }}>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Agent configuration and connection status</p>
      </div>

      {/* Agent Status */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h3>🤖 Agent Status</h3>
        </div>
        <div className="card-body">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className={`status-dot ${status?.is_busy ? '' : 'connected'}`}
              style={{ width: 12, height: 12 }} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {status?.is_busy ? 'Investigation in progress...' : 'Idle — Ready for alerts'}
            </span>
          </div>
          {status?.running_investigations?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {status.running_investigations.map((inv) => (
                <div key={inv.id} style={{ fontSize: 13, color: 'var(--text-secondary)', padding: '4px 0' }}>
                  📌 {inv.incident?.slice(0, 80)}...
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* LLM Providers */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h3>🧠 LLM Providers</h3>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="spinner" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {config?.llm_providers?.map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0' }}>
                  <span className={`status-dot ${p.configured ? 'connected' : ''}`} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>{p.name}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {p.configured ? 'Configured' : 'Not configured'}
                  </span>
                </div>
              )) || (
                <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>
                  Unable to load configuration
                </span>
              )}
            </div>
          )}
          <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
            API keys are configured via the <code>.env</code> file. The agent falls back through providers in order.
          </p>
        </div>
      </div>

      {/* Cluster Connection */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h3>🔗 Cluster Endpoints</h3>
        </div>
        <div className="card-body">
          <div className="form-group">
            <label>Prometheus URL</label>
            <input className="form-input" value={config?.prometheus_url || 'http://localhost:9090'} readOnly />
          </div>
          <div className="form-group">
            <label>Loki URL</label>
            <input className="form-input" value={config?.loki_url || 'http://localhost:3100'} readOnly />
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
            These endpoints are configured via environment variables. Update <code>.env</code> and restart the backend.
          </p>
        </div>
      </div>

      {/* About */}
      <div className="card">
        <div className="card-header">
          <h3>ℹ️ About</h3>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            <strong>LangGraph RCA Agent v1.0</strong><br />
            An intelligent, autonomous Root Cause Analysis agent powered by LangGraph, Kubernetes, and LLMs.
            This agent hooks into Prometheus AlertManager to automatically investigate production incidents,
            query logs and cluster state, and generate detailed root cause analyses.
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────

function App() {
  const [page, setPage] = useState('dashboard')
  const [selectedReportId, setSelectedReportId] = useState(null)
  const { connected, messages } = useWebSocket()

  const navigate = (target, id = null) => {
    if (target === 'report-detail' && id) {
      setSelectedReportId(id)
      setPage('report-detail')
    } else {
      setSelectedReportId(null)
      setPage(target)
    }
  }

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage wsMessages={messages} onNavigate={navigate} />
      case 'reports':
        return <ReportsPage onNavigate={navigate} />
      case 'report-detail':
        return <ReportDetailPage reportId={selectedReportId} onBack={() => navigate('reports')} />
      case 'alerts':
        return <AlertsPage />
      case 'settings':
        return <SettingsPage />
      default:
        return <DashboardPage wsMessages={messages} onNavigate={navigate} />
    }
  }

  return (
    <div className="app-layout">
      <Sidebar page={page} setPage={(p) => navigate(p)} connected={connected} />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  )
}

export default App
