import { useState, useEffect } from 'react'

export default function Admin() {
  const [config, setConfig] = useState(null)
  const [usage, setUsage] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [seedStatus, setSeedStatus] = useState(null)
  const [seedDetail, setSeedDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)

  useEffect(() => {
    Promise.all([
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
      .finally(() => setLoading(false))
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

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center text-slate-600">
        Loading admin…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-3xl font-bold text-slate-900">Admin – Knowledge Base</h1>
      <p className="mt-2 text-slate-600">
        Configure and manage the CoE knowledge base. Project directory and indexing are driven by your backend .env (PINECONE_PROJECT_DIR, etc.).
      </p>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 p-4 text-red-800">
          {error}
        </div>
      )}

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
    </div>
  )
}
