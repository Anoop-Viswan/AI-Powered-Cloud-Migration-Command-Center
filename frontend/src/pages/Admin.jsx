import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function Admin() {
  const [activeTab, setActiveTab] = useState('assessments')
  const [config, setConfig] = useState(null)
  const [usage, setUsage] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [seedStatus, setSeedStatus] = useState(null)
  const [seedDetail, setSeedDetail] = useState(null)
  const [assessmentsSummary, setAssessmentsSummary] = useState(null)
  const [assessmentsList, setAssessmentsList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)

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
    ])
      .then(([c, u, m, s]) => {
        setConfig(c)
        setUsage(u)
        setManifest(m)
        if (s.status && s.status !== 'idle') setSeedDetail(s)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    loadAssessments()
    loadKb().finally(() => setLoading(false))
  }, [])

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
      done: 'bg-emerald-100 text-emerald-800',
      error: 'bg-red-100 text-red-800',
      researching: 'bg-amber-100 text-amber-800',
      summarizing: 'bg-amber-100 text-amber-800',
      research_done: 'bg-slate-100 text-slate-700',
      draft: 'bg-slate-100 text-slate-600',
    }
    const label = status === 'done' ? 'Completed' : status === 'error' ? 'Error' : status.replace('_', ' ')
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] || 'bg-slate-100 text-slate-600'}`}>
        {label}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center text-slate-600">
        Loading admin…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-3xl font-bold text-slate-900">Admin Command Center</h1>
      <p className="mt-2 text-slate-600">
        Assessments overview and knowledge base management.
      </p>

      <div className="mt-6 flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('assessments')}
          className={`px-4 py-2 font-medium transition ${
            activeTab === 'assessments'
              ? 'border-b-2 border-emerald-600 text-emerald-700'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Assessments
        </button>
        <button
          onClick={() => setActiveTab('kb')}
          className={`px-4 py-2 font-medium transition ${
            activeTab === 'kb'
              ? 'border-b-2 border-emerald-600 text-emerald-700'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Knowledge Base
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 p-4 text-red-800">
          {error}
        </div>
      )}

      {activeTab === 'assessments' && (
        <div className="mt-8 space-y-8">
          {/* Scorecards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Total</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{assessmentsSummary?.total ?? 0}</p>
              <p className="mt-1 text-xs text-slate-500">Assessments</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm">
              <p className="text-sm font-medium text-emerald-700">Completed</p>
              <p className="mt-1 text-2xl font-bold text-emerald-800">{assessmentsSummary?.done ?? 0}</p>
              <p className="mt-1 text-xs text-emerald-600">Done</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">
              <p className="text-sm font-medium text-amber-700">In progress</p>
              <p className="mt-1 text-2xl font-bold text-amber-800">{assessmentsSummary?.in_progress ?? 0}</p>
              <p className="mt-1 text-xs text-amber-600">Draft / Research / Summarize</p>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50/50 p-5 shadow-sm">
              <p className="text-sm font-medium text-red-700">Errors</p>
              <p className="mt-1 text-2xl font-bold text-red-800">{assessmentsSummary?.error ?? 0}</p>
              <p className="mt-1 text-xs text-red-600">Failed</p>
            </div>
          </div>

          {/* Assessment list */}
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Assessment list</h2>
              <button
                onClick={loadAssessments}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Refresh
              </button>
            </div>
            {assessmentsList?.length === 0 ? (
              <p className="mt-6 text-center text-slate-500">No assessments yet. Start one from the Assessment page.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left">
                      <th className="pb-2 font-medium text-slate-600">Application</th>
                      <th className="pb-2 font-medium text-slate-600">Status</th>
                      <th className="pb-2 font-medium text-slate-600">Error</th>
                      <th className="pb-2 font-medium text-slate-600">Updated</th>
                      <th className="pb-2 font-medium text-slate-600"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {assessmentsList?.map((a) => (
                      <tr key={a.id} className="border-b border-slate-100">
                        <td className="py-3 font-medium text-slate-900">{a.app_name || '(unnamed)'}</td>
                        <td className="py-3">{statusBadge(a.status)}</td>
                        <td className="py-3 text-slate-500 max-w-[200px] truncate" title={a.error_message}>
                          {a.error_message || '—'}
                        </td>
                        <td className="py-3 text-slate-500">{formatTime(a.updated_at)}</td>
                        <td className="py-3">
                          <Link
                            to={`/assessment/${a.id}`}
                            className="text-emerald-600 font-medium hover:text-emerald-700"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {activeTab === 'kb' && (
        <div className="mt-8 space-y-8">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Configuration</h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div>
                <dt className="text-slate-500">Project directory</dt>
                <dd className="font-mono text-slate-900">{config?.project_dir ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Spend limit (USD)</dt>
                <dd>{config?.spend_limit ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Allow over limit</dt>
                <dd>{config?.allow_over_limit ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
            <p className="mt-4 text-xs text-slate-500">
              Edit .env in the project root to change PINECONE_PROJECT_DIR, PINECONE_SPEND_LIMIT, PINECONE_ALLOW_OVER_LIMIT.
            </p>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Usage</h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div>
                <dt className="text-slate-500">Estimated spend (USD)</dt>
                <dd className="font-semibold">${usage?.estimated_spend_usd ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Read units / Write units</dt>
                <dd>{usage?.read_units ?? 0} / {usage?.write_units ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-500">At or over limit</dt>
                <dd>{usage?.at_or_over_limit ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Index (seed)</h2>
            <p className="mt-2 text-sm text-slate-600">
              Re-index all documents from the project directory. Run after adding or changing files. Status updates automatically.
            </p>
            <button
              onClick={runSeed}
              disabled={!config?.project_dir || seedStatus === 'Starting…' || polling}
              className="mt-4 rounded-lg bg-slate-800 px-4 py-2 font-medium text-white hover:bg-slate-900 disabled:opacity-50"
            >
              {polling ? 'Indexing…' : 'Run seed (re-index)'}
            </button>
            {seedStatus && !seedDetail && <p className="mt-2 text-sm text-slate-600">{seedStatus}</p>}
            {seedDetail?.status === 'running' && (
              <div className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                Indexing in progress… This may take 30–60 seconds. Page will update when done.
              </div>
            )}
            {seedDetail?.status === 'completed' && (
              <div className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
                <strong>Success.</strong> Upserted {seedDetail.records_upserted ?? '—'} chunks. You can search the knowledge base now.
              </div>
            )}
            {seedDetail?.status === 'failed' && (
              <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">
                <strong>Failed:</strong> {seedDetail.error ?? 'Unknown error'}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Manifest (applications)</h2>
            <p className="mt-2 text-sm text-slate-600">
              Applications defined in manifest.json in the project directory.
            </p>
            <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-100 p-4 text-xs text-slate-800">
              {JSON.stringify(manifest?.applications ?? {}, null, 2)}
            </pre>
          </section>
        </div>
      )}
    </div>
  )
}
