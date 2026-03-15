import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function Admin() {
  const [activeTab, setActiveTab] = useState('assessments')
  const [config, setConfig] = useState(null)
  const [usage, setUsage] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [seedStatus, setSeedStatus] = useState(null)
  const [seedDetail, setSeedDetail] = useState(null)
  const [featureStatus, setFeatureStatus] = useState(null)
  const [reloadEnvLoading, setReloadEnvLoading] = useState(false)
  const [assessmentsSummary, setAssessmentsSummary] = useState(null)
  const [assessmentsList, setAssessmentsList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [cleanupMessage, setCleanupMessage] = useState(null)
  const [diagnosticsSummary, setDiagnosticsSummary] = useState(null)
  const [diagnosticsRequests, setDiagnosticsRequests] = useState([])
  const [diagnosticsInterfaces, setDiagnosticsInterfaces] = useState(null)
  const [diagnosticsConfig, setDiagnosticsConfig] = useState(null)
  const [diagnosticsPatterns, setDiagnosticsPatterns] = useState(null)
  const [diagnosticsPeriod, setDiagnosticsPeriod] = useState('24h')
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false)
  const [diagnosticsLastFetch, setDiagnosticsLastFetch] = useState(null)
  const [diagnosticsRequestDetail, setDiagnosticsRequestDetail] = useState(null)
  const [diagnosticsConfigForm, setDiagnosticsConfigForm] = useState({
    daily_token_limit: 500000,
    daily_cost_limit_usd: 5,
    alert_at_percent: 80,
    tavily_daily_limit: 100,
  })
  const [diagnosticsConfigSaving, setDiagnosticsConfigSaving] = useState(false)

  const loadDiagnostics = () => {
    setDiagnosticsLoading(true)
    setDiagnosticsLastFetch(Date.now())
    const period = diagnosticsPeriod
    Promise.all([
      fetch(`/api/admin/diagnostics/summary?period=${period}`).then((r) => r.json()),
      fetch(`/api/admin/diagnostics/requests?limit=50`).then((r) => r.json()),
      fetch(`/api/admin/diagnostics/interfaces?period=${period}`).then((r) => r.json()),
      fetch('/api/admin/diagnostics/config').then((r) => r.json()),
      fetch(`/api/admin/diagnostics/patterns?period=${period}`).then((r) => r.json()),
    ])
      .then(([summary, reqData, interfaces, config, patterns]) => {
        setDiagnosticsSummary(summary)
        setDiagnosticsRequests(reqData.requests || [])
        setDiagnosticsInterfaces(interfaces)
        setDiagnosticsPatterns(patterns)
        setDiagnosticsConfig(config)
        setDiagnosticsConfigForm({
          daily_token_limit: parseInt(config?.daily_token_limit, 10) || 500000,
          daily_cost_limit_usd: parseFloat(config?.daily_cost_limit_usd) || 5,
          alert_at_percent: parseInt(config?.alert_at_percent, 10) || 80,
          tavily_daily_limit: parseInt(config?.tavily_daily_limit, 10) || 100,
        })
      })
      .catch(() => {})
      .finally(() => setDiagnosticsLoading(false))
  }

  const saveDiagnosticsConfig = async () => {
    setDiagnosticsConfigSaving(true)
    try {
      const r = await fetch('/api/admin/diagnostics/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(diagnosticsConfigForm),
      })
      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        throw new Error(d.detail || 'Save failed')
      }
      loadDiagnostics()
    } catch (e) {
      setError(e.message)
    } finally {
      setDiagnosticsConfigSaving(false)
    }
  }

  const loadAssessments = () => {
    Promise.all([
      fetch('/api/admin/assessments/summary').then((r) => r.json()),
      fetch('/api/admin/assessments').then((r) => r.json()),
    ])
      .then(([summary, list]) => {
        setAssessmentsSummary(summary)
        setAssessmentsList(list)
      })
      .catch(() => {})
  }

  const loadKb = () => {
    return Promise.all([
      fetch('/api/admin/config').then((r) => r.json()),
      fetch('/api/admin/usage').then((r) => r.json()),
      fetch('/api/admin/manifest').then((r) => r.json()),
      fetch('/api/admin/seed/status').then((r) => r.json()),
      fetch('/api/admin/feature-status').then((r) => r.json()),
    ])
      .then(([c, u, m, s, fs]) => {
        setConfig(c)
        setUsage(u)
        setManifest(m)
        if (s.status && s.status !== 'idle') setSeedDetail(s)
        setFeatureStatus(fs)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    loadAssessments()
    loadKb().finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (activeTab === 'diagnostics') loadDiagnostics()
  }, [activeTab, diagnosticsPeriod])

  // Poll seed status when running
  useEffect(() => {
    if (!polling) return
    const id = setInterval(async () => {
      try {
        const res = await fetch('/api/admin/seed/status')
        const data = await res.json()
        setSeedDetail(data)
        if (data.status === 'completed' || data.status === 'failed') setPolling(false)
      } catch {
        setPolling(false)
      }
    }, 2000)
    return () => clearInterval(id)
  }, [polling])

  async function handleDeleteAssessment(id) {
    if (!window.confirm('Delete this assessment? This cannot be undone.')) return
    setDeletingId(id)
    setError(null)
    try {
      const r = await fetch(`/api/assessment/${id}`, { method: 'DELETE' })
      if (!r.ok) {
        const data = await r.json().catch(() => ({}))
        throw new Error(data.detail || 'Delete failed')
      }
      loadAssessments()
    } catch (e) {
      setError(e.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleCleanupDrafts() {
    if (!window.confirm('Delete all draft assessments? This cannot be undone.')) return
    setCleanupMessage(null)
    setError(null)
    try {
      const r = await fetch('/api/admin/assessments/cleanup?status=draft', { method: 'POST' })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || 'Cleanup failed')
      setCleanupMessage(`Removed ${data.deleted ?? 0} draft(s).`)
      loadAssessments()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleReloadEnv() {
    setReloadEnvLoading(true)
    setError(null)
    try {
      const r = await fetch('/api/admin/reload-env', { method: 'POST' })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || 'Reload failed')
      await loadKb()
    } catch (e) {
      setError(e.message)
    } finally {
      setReloadEnvLoading(false)
    }
  }

  async function runSeed() {
    setSeedStatus('Starting…')
    setSeedDetail(null)
    setError(null)
    try {
      const res = await fetch('/api/admin/seed', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Seed failed')
      setSeedStatus('Indexing…')
      setPolling(true)
    } catch (e) {
      setError(e.message)
      setSeedStatus(null)
    }
  }

  function formatTime(iso) {
    if (!iso) return '—'
    try {
      const d = new Date(iso)
      const now = new Date()
      const diffMs = now - d
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)
      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`
      return d.toLocaleDateString()
    } catch {
      return iso
    }
  }

  function statusBadge(status) {
    const styles = {
      submitted: 'bg-teal-500/20 text-teal-300',
      done: 'text-emerald-400',
      error: 'text-red-400',
      researching: 'text-amber-400',
      summarizing: 'text-amber-400',
      research_done: 'text-slate-300',
      draft: 'text-slate-400',
    }
    const labels = {
      done: 'report_done',
      error: 'error',
      submitted: 'submitted',
    }
    const label = labels[status] || (status ? status.replace('_', ' ') : '—')
    return (
      <span className={`text-sm font-medium ${styles[status] || 'text-slate-400'}`}>
        {label}
      </span>
    )
  }

  // Sort: submitted first, then done, then error, then in-progress, then draft; within same status by updated_at desc
  const statusOrder = { submitted: 0, done: 1, error: 2, researching: 3, summarizing: 4, research_done: 5, draft: 6 }
  const sortedList = [...(assessmentsList || [])].sort((a, b) => {
    const oa = statusOrder[a.status] ?? 7
    const ob = statusOrder[b.status] ?? 7
    if (oa !== ob) return oa - ob
    return (b.updated_at || '').localeCompare(a.updated_at || '')
  })

  function shortId(id) {
    if (!id) return '—'
    return id.length >= 8 ? id.slice(0, 8) : id
  }

  if (loading) {
    return (
      <div className="min-h-[200px] flex items-center justify-center text-slate-400">
        Loading admin…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl">
      {/* Dark header – wireframe Admin Command Center */}
      <header className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 px-6 py-4 text-white">
        <h1 className="text-xl font-bold">Admin Command Center</h1>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg bg-white/10 p-0.5">
            <button
              onClick={() => setActiveTab('assessments')}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                activeTab === 'assessments' ? 'bg-teal-500 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              Assessments
            </button>
            <button
              onClick={() => setActiveTab('kb')}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                activeTab === 'kb' ? 'bg-teal-500 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              Knowledge Base
            </button>
            <button
              onClick={() => setActiveTab('diagnostics')}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                activeTab === 'diagnostics' ? 'bg-teal-500 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              Diagnostics
            </button>
          </div>
          <button
            onClick={activeTab === 'assessments' ? loadAssessments : activeTab === 'diagnostics' ? loadDiagnostics : loadKb}
            className="rounded-lg border border-white/30 bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/20"
          >
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="mx-4 mt-4 rounded-lg bg-red-500/10 border border-red-500/30 p-4 text-red-200">
          {error}
        </div>
      )}

      {activeTab === 'assessments' && (
        <div className="bg-slate-800">
          {/* Summary cards – dark slate */}
          <div className="grid grid-cols-2 gap-4 p-6 md:grid-cols-3">
            <div className="rounded-lg bg-slate-700/80 p-4 text-white">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Total</p>
              <p className="mt-1 text-2xl font-bold">{assessmentsSummary?.total ?? 0}</p>
              <p className="mt-0.5 text-sm text-slate-400">Migration requests</p>
            </div>
            <div className="rounded-lg bg-slate-700/80 p-4 text-white">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">New (submitted)</p>
              <p className="mt-1 text-2xl font-bold">{assessmentsSummary?.submitted ?? 0}</p>
              <p className="mt-0.5 text-sm text-slate-400">Awaiting research</p>
            </div>
            <div className="rounded-lg bg-slate-700/80 p-4 text-white">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Report done</p>
              <p className="mt-1 text-2xl font-bold">{assessmentsSummary?.done ?? 0}</p>
              <p className="mt-0.5 text-sm text-slate-400">
                {assessmentsSummary?.error > 0 ? `${assessmentsSummary.error} error` : 'Completed'}
              </p>
            </div>
          </div>

          {/* Clean up drafts */}
          <div className="flex flex-wrap items-center gap-4 px-6 pb-2">
            <button
              onClick={handleCleanupDrafts}
              className="rounded-lg border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-200 hover:bg-red-500/20"
            >
              Clean up all drafts
            </button>
            {cleanupMessage && (
              <span className="text-sm text-slate-400">{cleanupMessage}</span>
            )}
          </div>

          {/* Table – wireframe columns: ID, App name, Status, Submitted, Updated, Actions */}
          <div className="overflow-x-auto px-6 pb-6">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-600 text-left">
                  <th className="pb-3 pr-4 font-semibold text-slate-300">ID</th>
                  <th className="pb-3 pr-4 font-semibold text-slate-300">App name</th>
                  <th className="pb-3 pr-4 font-semibold text-slate-300">Status</th>
                  <th className="pb-3 pr-4 font-semibold text-slate-300">Submitted</th>
                  <th className="pb-3 pr-4 font-semibold text-slate-300">Updated</th>
                  <th className="pb-3 font-semibold text-slate-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedList.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-400">
                      No assessments yet. Start one from the Assessment page.
                    </td>
                  </tr>
                ) : (
                  sortedList.map((a) => (
                    <tr key={a.id} className="border-b border-slate-700 text-slate-300">
                      <td className="py-3 pr-4 font-mono text-xs text-slate-400">{shortId(a.id)}</td>
                      <td className="py-3 pr-4 font-medium text-white">
                        {a.app_name || (a.status === 'draft' ? '(Draft)' : '(Unnamed)')}
                      </td>
                      <td className="py-3 pr-4">{statusBadge(a.status)}</td>
                      <td className="py-3 pr-4 text-slate-400">
                        {a.status === 'submitted' ? formatTime(a.updated_at) : '—'}
                      </td>
                      <td className="py-3 pr-4 text-slate-400">{formatTime(a.updated_at)}</td>
                      <td className="py-3">
                        <Link
                          to={`/admin/assessment/${a.id}`}
                          className="font-medium text-teal-400 hover:text-teal-300"
                        >
                          Open
                        </Link>
                        {a.status === 'done' && (
                          <>
                            <span className="mx-2 text-slate-600">|</span>
                            <a
                              href={`/api/assessment/${a.id}/report?format=docx`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-slate-400 hover:text-white"
                            >
                              Download
                            </a>
                          </>
                        )}
                        <span className="mx-2 text-slate-600">|</span>
                        <button
                          type="button"
                          onClick={() => handleDeleteAssessment(a.id)}
                          disabled={deletingId === a.id}
                          className="font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
                        >
                          {deletingId === a.id ? '…' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'kb' && (
        <div className="grid gap-6 p-6 md:grid-cols-2 bg-slate-800">
          {/* Feature status: Pinecone, LLM, LangSmith, Tavily – informed messages when not configured */}
          {featureStatus && (
            <section className="rounded-lg border border-slate-600 bg-slate-700/80 p-5 text-white md:col-span-2">
              <h2 className="text-lg font-semibold text-white">Feature status</h2>
              <p className="mt-1 text-sm text-slate-400">
                Which services are configured and why others are not. Add missing keys in <code className="rounded bg-slate-800 px-1">.env</code>; see <code className="rounded bg-slate-800 px-1">docs/ENV_REFERENCE.md</code>. After editing .env, click &quot;Reload .env&quot; to pick up changes without restarting the server.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={handleReloadEnv}
                  disabled={reloadEnvLoading}
                  className="rounded-lg border border-slate-500 bg-slate-700 px-3 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-50"
                >
                  {reloadEnvLoading ? 'Reloading…' : 'Reload .env'}
                </button>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {['pinecone', 'llm', 'langsmith', 'tavily'].map((key) => {
                  const f = featureStatus[key]
                  if (!f) return null
                  const status = f.status
                  const isOk = status === 'ok'
                  const isDisabled = status === 'disabled'
                  const isLimit = status === 'limit_reached'
                  const label = key.charAt(0).toUpperCase() + key.slice(1)
                  return (
                    <div key={key} className={`rounded-lg p-3 ${isOk ? 'bg-emerald-900/30 border border-emerald-600/50' : isLimit ? 'bg-amber-900/30 border border-amber-600/50' : 'bg-slate-800 border border-slate-600'}`}>
                      <p className="text-sm font-medium text-white">{label}</p>
                      <p className="mt-1 text-xs text-slate-300">{f.message}</p>
                      {f.instruction && (
                        <p className="mt-2 text-xs text-amber-200/90">{f.instruction}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          <section className="rounded-lg border border-slate-600 bg-slate-700/80 p-5 text-white">
            <h2 className="text-lg font-semibold text-white">KB Config &amp; Seed</h2>
            <dl className="mt-4 space-y-2 text-sm text-slate-300">
              <div>
                <dt className="text-slate-400">Project directory</dt>
                <dd className="font-mono text-slate-200">{config?.project_dir ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Spend limit (USD)</dt>
                <dd>{config?.spend_limit ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Allow over limit</dt>
                <dd>{config?.allow_over_limit ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
            <p className="mt-4 text-xs text-slate-400">
              Edit .env for PINECONE_PROJECT_DIR, PINECONE_SPEND_LIMIT, PINECONE_ALLOW_OVER_LIMIT.
            </p>
            <button
              onClick={runSeed}
              disabled={!config?.project_dir || seedStatus === 'Starting…' || polling}
              className="mt-4 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
            >
              {polling ? 'Indexing…' : 'Run seed (re-index)'}
            </button>
            {seedStatus && !seedDetail && <p className="mt-2 text-sm text-slate-400">{seedStatus}</p>}
            {seedDetail?.status === 'running' && (
              <div className="mt-3 rounded-lg bg-amber-500/20 p-3 text-sm text-amber-200">
                Indexing in progress… This may take 30–60 seconds.
              </div>
            )}
            {seedDetail?.status === 'completed' && (
              <div className="mt-3 rounded-lg bg-emerald-500/20 p-3 text-sm text-emerald-200">
                <strong>Success.</strong> Upserted {seedDetail.records_upserted ?? '—'} chunks.
              </div>
            )}
            {seedDetail?.status === 'failed' && (
              <div className="mt-3 rounded-lg bg-red-500/20 p-3 text-sm text-red-200">
                <strong>Failed:</strong> {seedDetail.error ?? 'Unknown error'}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-600 bg-slate-700/80 p-5 text-white">
            <h2 className="text-lg font-semibold text-white">Usage</h2>
            <dl className="mt-4 space-y-2 text-sm text-slate-300">
              <div>
                <dt className="text-slate-400">Estimated spend (USD)</dt>
                <dd className="font-semibold text-white">${usage?.estimated_spend_usd ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Read units / Write units</dt>
                <dd>{usage?.read_units ?? 0} / {usage?.write_units ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-400">At or over limit</dt>
                <dd>{usage?.at_or_over_limit ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border border-slate-600 bg-slate-700/80 p-5 text-white md:col-span-2">
            <h2 className="text-lg font-semibold text-white">Manifest (applications)</h2>
            <p className="mt-1 text-sm text-slate-400">
              Applications defined in manifest.json in the project directory.
            </p>
            <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-300">
              {JSON.stringify(manifest?.applications ?? {}, null, 2)}
            </pre>
          </section>
        </div>
      )}

      {activeTab === 'diagnostics' && (
        <div className="bg-slate-800 text-white">
          {/* Toolbar: period + data as of */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700 px-6 py-4">
            <div className="flex gap-2">
              {['24h', '7d', '30d'].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setDiagnosticsPeriod(p)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium ${
                    diagnosticsPeriod === p ? 'bg-teal-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {p === '24h' ? 'Last 24h' : p === '7d' ? 'Last 7 days' : 'Last 30 days'}
                </button>
              ))}
            </div>
            <span className="text-sm text-slate-400">
              {diagnosticsLastFetch
                ? `Data as of ${Math.max(0, Math.round((Date.now() - diagnosticsLastFetch) / 60000))} min ago`
                : '—'}
            </span>
          </div>

          {diagnosticsLoading ? (
            <div className="p-8 text-center text-slate-400">Loading diagnostics…</div>
          ) : (
            <div className="space-y-6 p-6">
              {/* Alerts (wireframe: Active alerts, warning/critical) */}
              {diagnosticsSummary?.alerts?.length > 0 && (
                <section>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Active alerts</p>
                  <div className="space-y-2">
                    {diagnosticsSummary.alerts.map((a, i) => (
                      <div
                        key={i}
                        className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 ${
                          a.type === 'exceeded'
                            ? 'border-red-500/50 bg-red-500/10'
                            : 'border-amber-500/50 bg-amber-500/10'
                        }`}
                      >
                        <div>
                          <strong className="text-slate-200">
                            {a.type === 'exceeded' ? 'Limit exceeded' : 'Approaching limit'}
                          </strong>
                          <p className="mt-0.5 text-sm text-slate-300">
                            {a.metric === 'daily_token_limit' &&
                              `Daily token usage at ${Math.round((Number(a.current) / Number(a.limit)) * 100)}% of limit (${Number(a.current).toLocaleString()} / ${Number(a.limit).toLocaleString()} tokens).`}
                            {a.metric === 'daily_cost_usd' &&
                              `Daily cost limit exceeded: $${a.current} / $${a.limit} (LLM approximate).`}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Summary cards (wireframe: 4 cards with label, value, sub) */}
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-slate-700/80 p-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-400">LLM calls</div>
                  <div className="mt-1 text-2xl font-bold text-white">
                    {diagnosticsSummary?.llm?.total_calls ?? 0}
                  </div>
                  <div className="mt-0.5 text-sm text-slate-400">
                    {diagnosticsSummary?.llm?.by_operation?.length
                      ? diagnosticsSummary.llm.by_operation
                          .map((o) => `${o.operation.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}: ${o.calls}`)
                          .join(' · ')
                      : '—'}
                  </div>
                </div>
                <div className="rounded-lg bg-slate-700/80 p-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Tokens ({diagnosticsPeriod})
                  </div>
                  <div className="mt-1 text-2xl font-bold text-white">
                    {((diagnosticsSummary?.llm?.total_input_tokens ?? 0) + (diagnosticsSummary?.llm?.total_output_tokens ?? 0)).toLocaleString()}
                  </div>
                  <div className="mt-0.5 text-sm text-slate-400">
                    In: {(diagnosticsSummary?.llm?.total_input_tokens ?? 0).toLocaleString()} · Out:{' '}
                    {(diagnosticsSummary?.llm?.total_output_tokens ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="rounded-lg border border-teal-500/50 bg-slate-700/80 p-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Approx. cost ({diagnosticsPeriod})
                  </div>
                  <div className="mt-1 text-2xl font-bold text-white">
                    ${diagnosticsSummary?.llm?.approx_cost_usd ?? '0.00'}
                  </div>
                  <div className="mt-0.5 text-sm text-slate-400">LLM only · model pricing</div>
                </div>
                <div className="rounded-lg bg-slate-700/80 p-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Tavily · Pinecone</div>
                  <div className="mt-1 text-2xl font-bold text-white">
                    {diagnosticsSummary?.tavily?.total_calls ?? 0} · {diagnosticsInterfaces?.pinecone?.queries ?? 0}
                  </div>
                  <div className="mt-0.5 text-sm text-slate-400">Search calls · KB queries</div>
                </div>
              </div>

              {/* External interfaces (wireframe: LLM, Tavily, Pinecone with stats) */}
              <section>
                <h3 className="mb-3 text-base font-semibold text-white">External interfaces</h3>
                <p className="mb-3 text-xs text-slate-500">
                  LLM status (when period is Last 24h): <strong className="text-slate-400">OK</strong> = within limits; <strong className="text-amber-400">Near limit</strong> = at or above your &quot;Alert when usage reaches (%)&quot; of the daily token/cost limit, or has errors; <strong className="text-red-400">Over limit</strong> = daily token or cost limit exceeded.
                </p>
                <div className="grid gap-4 md:grid-cols-3">
                  {diagnosticsInterfaces?.llm && (
                    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-600 bg-slate-700/50 p-4">
                      <span className="w-full text-sm font-medium text-slate-200">
                        LLM{diagnosticsInterfaces.llm.model ? ` (${diagnosticsInterfaces.llm.model})` : ''}
                      </span>
                      <div className="flex flex-wrap gap-4">
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.llm.calls}</span><div className="text-xs text-slate-400">Calls</div></div>
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.llm.p95_latency_ms != null ? `${(diagnosticsInterfaces.llm.p95_latency_ms / 1000).toFixed(2)}s` : '—'}</span><div className="text-xs text-slate-400">p95 latency</div></div>
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.llm.errors}</span><div className="text-xs text-slate-400">Errors</div></div>
                        <div><span className="text-lg font-bold text-white">${diagnosticsInterfaces.llm.approx_cost_usd ?? '—'}</span><div className="text-xs text-slate-400">Approx. cost</div></div>
                      </div>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        diagnosticsInterfaces.llm.status === 'exceeded' ? 'bg-red-500/20 text-red-200' :
                        diagnosticsInterfaces.llm.status === 'warn' ? 'bg-amber-500/20 text-amber-200' : 'bg-emerald-500/20 text-emerald-200'
                      }`}>
                        {diagnosticsInterfaces.llm.status === 'exceeded' ? 'Over limit' : diagnosticsInterfaces.llm.status === 'warn' ? 'Near limit' : 'OK'}
                      </span>
                    </div>
                  )}
                  {diagnosticsInterfaces?.tavily && (
                    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-600 bg-slate-700/50 p-4">
                      <span className="w-full text-sm font-medium text-slate-200">Tavily (web search)</span>
                      <div className="flex flex-wrap gap-4">
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.tavily.calls}</span><div className="text-xs text-slate-400">Calls</div></div>
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.tavily.avg_latency_ms != null ? `${(diagnosticsInterfaces.tavily.avg_latency_ms / 1000).toFixed(2)}s` : '—'}</span><div className="text-xs text-slate-400">Avg latency</div></div>
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.tavily.errors}</span><div className="text-xs text-slate-400">Errors</div></div>
                        <div><span className="text-lg font-bold text-white">—</span><div className="text-xs text-slate-400">Cost</div></div>
                      </div>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${diagnosticsInterfaces.tavily.status === 'warn' ? 'bg-amber-500/20 text-amber-200' : 'bg-emerald-500/20 text-emerald-200'}`}>
                        {diagnosticsInterfaces.tavily.status === 'warn' ? 'Errors' : 'OK'}
                      </span>
                    </div>
                  )}
                  {diagnosticsInterfaces?.pinecone && (
                    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-600 bg-slate-700/50 p-4">
                      <span className="w-full text-sm font-medium text-slate-200">Pinecone (KB)</span>
                      <div className="flex flex-wrap gap-4">
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.pinecone.queries ?? 0}</span><div className="text-xs text-slate-400">Queries</div></div>
                        <div><span className="text-lg font-bold text-white">—</span><div className="text-xs text-slate-400">p95 latency</div></div>
                        <div><span className="text-lg font-bold text-white">{diagnosticsInterfaces.pinecone.errors ?? 0}</span><div className="text-xs text-slate-400">Errors</div></div>
                        <div><span className="text-lg font-bold text-white">—</span><div className="text-xs text-slate-400">Read units</div></div>
                      </div>
                      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-200">OK</span>
                    </div>
                  )}
                </div>
              </section>

              {/* Thresholds & alerts (wireframe: form) */}
              <section>
                <h3 className="mb-1 text-base font-semibold text-white">Thresholds &amp; alerts</h3>
                <p className="mb-4 text-sm text-slate-400">
                  Configure limits and get alerted when usage approaches or exceeds them. Helps avoid surprise bills and rate limits.
                </p>
                <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-300">Daily token limit</label>
                    <input
                      type="number"
                      value={diagnosticsConfigForm.daily_token_limit}
                      onChange={(e) => setDiagnosticsConfigForm((f) => ({ ...f, daily_token_limit: parseInt(e.target.value, 10) || 0 }))}
                      placeholder="e.g. 500000"
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-white placeholder-slate-500"
                    />
                    <span className="mt-0.5 block text-xs text-slate-500">Total LLM tokens (in + out) per day</span>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-300">Daily cost limit (USD)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={diagnosticsConfigForm.daily_cost_limit_usd}
                      onChange={(e) => setDiagnosticsConfigForm((f) => ({ ...f, daily_cost_limit_usd: parseFloat(e.target.value) || 0 }))}
                      placeholder="e.g. 5.00"
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-white placeholder-slate-500"
                    />
                    <span className="mt-0.5 block text-xs text-slate-500">Approximate LLM cost cap per day</span>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-300">Alert when usage reaches (%)</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={diagnosticsConfigForm.alert_at_percent}
                      onChange={(e) => setDiagnosticsConfigForm((f) => ({ ...f, alert_at_percent: parseInt(e.target.value, 10) || 80 }))}
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-white"
                    />
                    <span className="mt-0.5 block text-xs text-slate-500">Warn at e.g. 80% of limit</span>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-300">Tavily daily call limit</label>
                    <input
                      type="number"
                      value={diagnosticsConfigForm.tavily_daily_limit}
                      onChange={(e) => setDiagnosticsConfigForm((f) => ({ ...f, tavily_daily_limit: parseInt(e.target.value, 10) || 0 }))}
                      placeholder="e.g. 100"
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-white placeholder-slate-500"
                    />
                    <span className="mt-0.5 block text-xs text-slate-500">Optional; leave 0 for no cap</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={saveDiagnosticsConfig}
                  disabled={diagnosticsConfigSaving}
                  className="mt-4 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
                >
                  {diagnosticsConfigSaving ? 'Saving…' : 'Save thresholds'}
                </button>
              </section>

              {/* Patterns (wireframe: usage over time chart + top consumers table) */}
              <section>
                <h3 className="mb-3 text-base font-semibold text-white">Patterns</h3>
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <p className="mb-2 text-sm text-slate-400">Usage over time (tokens / cost)</p>
                    <div className="rounded-lg border border-slate-600 bg-slate-700/50 p-4">
                      {(diagnosticsPatterns?.usage_by_day?.length ?? 0) > 0 ? (
                        <div className="flex h-[160px] items-end gap-1" style={{ minHeight: '160px' }}>
                          {diagnosticsPatterns.usage_by_day.map((day) => {
                            const maxTokens = Math.max(...diagnosticsPatterns.usage_by_day.map((d) => d.tokens || 0), 1)
                            const pct = Math.round(((day.tokens || 0) / maxTokens) * 100)
                            const label = day.date ? new Date(day.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''
                            return (
                              <div key={day.date} className="flex flex-1 flex-col items-center gap-1" title={`${label}: ${(day.tokens || 0).toLocaleString()} tokens, $${(day.cost_usd || 0).toFixed(2)}`}>
                                <div className="w-full max-w-[32px] rounded-t bg-teal-500/80 transition-all" style={{ height: `${Math.max(pct, 4)}%`, minHeight: '4px' }} />
                                <span className="text-[10px] text-slate-400">{label}</span>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="flex h-[160px] items-center justify-center text-sm text-slate-500">
                          No usage data for this period. Run research or generate a report to see tokens/cost by day.
                        </div>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="mb-2 text-sm text-slate-400">Top consumers (by cost %)</p>
                    <div className="overflow-x-auto rounded-lg border border-slate-600">
                      <table className="w-full border-collapse text-sm">
                        <thead>
                          <tr className="border-b border-slate-600 bg-slate-700/80 text-left">
                            <th className="px-3 py-2 font-semibold text-slate-400">Operation</th>
                            <th className="px-3 py-2 font-semibold text-slate-400">Calls</th>
                            <th className="px-3 py-2 font-semibold text-slate-400">Tokens</th>
                            <th className="px-3 py-2 font-semibold text-slate-400">Cost</th>
                            <th className="px-3 py-2 font-semibold text-slate-400">%</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(diagnosticsPatterns?.top_consumers ?? []).length === 0 ? (
                            <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-500">No data</td></tr>
                          ) : (
                            diagnosticsPatterns.top_consumers.map((row, i) => (
                              <tr key={i} className="border-b border-slate-700 text-slate-300">
                                <td className="px-3 py-2">{row.operation}</td>
                                <td className="px-3 py-2">{row.calls}</td>
                                <td className="px-3 py-2">{row.tokens?.toLocaleString() ?? '—'}</td>
                                <td className="px-3 py-2">${row.cost_usd?.toFixed(2) ?? '—'}</td>
                                <td className="px-3 py-2 font-semibold text-teal-400">{row.cost_pct ?? 0}%</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </section>

              {/* Request log (wireframe: table with Time, Interface, Operation, Tokens in/out, Latency, Status, Assessment) + drill-down */}
              <section>
                <h3 className="mb-3 text-base font-semibold text-white">Request log (last 50)</h3>
                <div className="overflow-x-auto rounded-lg border border-slate-600">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-slate-600 bg-slate-700/80 text-left">
                        <th className="px-3 py-2 font-semibold text-slate-400">Time</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Interface</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Operation</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Tokens in / out</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Latency</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Status</th>
                        <th className="px-3 py-2 font-semibold text-slate-400">Assessment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diagnosticsRequests.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                            No calls yet. Run research, generate report, or use chat.
                          </td>
                        </tr>
                      ) : (
                        diagnosticsRequests.map((r, i) => (
                          <tr
                            key={r.id ?? i}
                            onClick={() => setDiagnosticsRequestDetail(r)}
                            className="cursor-pointer border-b border-slate-700 text-slate-300 hover:bg-slate-700/50"
                          >
                            <td className="px-3 py-2 text-xs text-slate-400">
                              {r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : '—'}
                            </td>
                            <td className="px-3 py-2">{r.interface === 'llm' ? 'LLM' : r.interface === 'tool' ? 'Tavily' : r.interface}</td>
                            <td className="px-3 py-2">{r.operation}</td>
                            <td className="px-3 py-2 text-slate-400">
                              {r.tokens_in != null || r.tokens_out != null
                                ? `${(r.tokens_in ?? 0).toLocaleString()} / ${(r.tokens_out ?? 0).toLocaleString()}`
                                : '—'}
                            </td>
                            <td className="px-3 py-2 text-slate-400">
                              {r.latency_ms != null ? (r.latency_ms >= 1000 ? `${(r.latency_ms / 1000).toFixed(2)}s` : `${r.latency_ms}ms`) : '—'}
                            </td>
                            <td className="px-3 py-2">
                              <span className={r.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}>{r.status}</span>
                            </td>
                            <td className="px-3 py-2">
                              {r.assessment_id ? (
                                <Link to={`/admin/assessment/${r.assessment_id}`} className="text-teal-400 underline hover:no-underline" onClick={(e) => e.stopPropagation()}>
                                  {r.assessment_id.slice(0, 8)}
                                </Link>
                              ) : (
                                '—'
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="mt-2 flex items-center justify-between text-sm text-slate-500">
                  <span>1–{diagnosticsRequests.length} of {diagnosticsRequests.length}</span>
                </div>
              </section>

              {/* LangSmith */}
              <section>
                <h3 className="mb-3 text-base font-semibold text-white">LangSmith</h3>
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm text-slate-200">
                    Full trace trees, token breakdown, and latency per step are available in LangSmith when tracing is enabled.
                  </span>
                  <a
                    href="https://smith.langchain.com/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-teal-400 hover:underline"
                  >
                    Open LangSmith project →
                  </a>
                </div>
              </section>
            </div>
          )}

          {/* Drill-down detail panel (double-click / click row) */}
          {diagnosticsRequestDetail && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
              onClick={() => setDiagnosticsRequestDetail(null)}
            >
              <div
                className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-slate-600 bg-slate-800 p-6 shadow-xl"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Request detail</h3>
                  <button type="button" onClick={() => setDiagnosticsRequestDetail(null)} className="rounded-lg bg-slate-600 px-3 py-1.5 text-sm text-white hover:bg-slate-500">Close</button>
                </div>
                <dl className="space-y-3 text-sm">
                  <div><dt className="text-slate-500">ID</dt><dd className="font-mono text-slate-200">{diagnosticsRequestDetail.id ?? '—'}</dd></div>
                  <div><dt className="text-slate-500">Timestamp</dt><dd className="font-mono text-slate-200">{diagnosticsRequestDetail.timestamp ? new Date(diagnosticsRequestDetail.timestamp).toISOString() : '—'}</dd></div>
                  <div><dt className="text-slate-500">Interface</dt><dd className="text-slate-200">{diagnosticsRequestDetail.interface}</dd></div>
                  <div><dt className="text-slate-500">Operation</dt><dd className="text-slate-200">{diagnosticsRequestDetail.operation}</dd></div>
                  {diagnosticsRequestDetail.model && <div><dt className="text-slate-500">Model</dt><dd className="text-slate-200">{diagnosticsRequestDetail.model}</dd></div>}
                  <div><dt className="text-slate-500">Tokens in / out</dt><dd className="text-slate-200">{diagnosticsRequestDetail.tokens_in != null || diagnosticsRequestDetail.tokens_out != null ? `${diagnosticsRequestDetail.tokens_in ?? '—'} / ${diagnosticsRequestDetail.tokens_out ?? '—'}` : '—'}</dd></div>
                  <div><dt className="text-slate-500">Latency</dt><dd className="text-slate-200">{diagnosticsRequestDetail.latency_ms != null ? `${diagnosticsRequestDetail.latency_ms} ms` : '—'}</dd></div>
                  <div><dt className="text-slate-500">Status</dt><dd className={diagnosticsRequestDetail.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}>{diagnosticsRequestDetail.status}</dd></div>
                  {diagnosticsRequestDetail.error_message && (
                    <div><dt className="text-slate-500">Error message</dt><dd className="rounded bg-red-500/10 p-2 font-mono text-xs text-red-200 whitespace-pre-wrap break-all">{diagnosticsRequestDetail.error_message}</dd></div>
                  )}
                  {diagnosticsRequestDetail.assessment_id && (
                    <div><dt className="text-slate-500">Assessment</dt><dd><Link to={`/admin/assessment/${diagnosticsRequestDetail.assessment_id}`} className="text-teal-400 underline hover:no-underline">{diagnosticsRequestDetail.assessment_id}</Link></dd></div>
                  )}
                  {diagnosticsRequestDetail.metadata && Object.keys(diagnosticsRequestDetail.metadata).length > 0 && (
                    <div><dt className="text-slate-500">Metadata</dt><dd className="rounded bg-slate-700/80 p-2 font-mono text-xs text-slate-300 whitespace-pre-wrap">{JSON.stringify(diagnosticsRequestDetail.metadata, null, 2)}</dd></div>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  )
}
