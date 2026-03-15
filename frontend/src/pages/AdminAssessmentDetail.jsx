import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'

const API = '/api'

function Section({ title, children }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-600">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  )
}

function Field({ label, value }) {
  const v = value ?? ''
  const display = Array.isArray(v) ? v.join(', ') : String(v)
  if (display === '') return null
  return (
    <div>
      <span className="font-medium text-slate-600">{label}:</span>{' '}
      <span className="text-slate-900">{display}</span>
    </div>
  )
}

export default function AdminAssessmentDetail() {
  const { id } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(null) // 'research' | 'summarize' | 'saveReport'
  const [reportEdit, setReportEdit] = useState('')
  // Live research progress (SSE events) for Cursor-style updates
  const [researchProgress, setResearchProgress] = useState([])
  // Human-in-the-loop: when diagram design asks for clarification
  const [clarificationQuestions, setClarificationQuestions] = useState([])
  const [clarificationAnswers, setClarificationAnswers] = useState({})
  // Quick fix for validation errors (e.g. missing contains_database_migration)
  const [quickFixDbMigration, setQuickFixDbMigration] = useState('')
  const [quickFixLoading, setQuickFixLoading] = useState(false)

  const loadAssessment = async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API}/assessment/${id}`)
      if (!r.ok) {
        if (r.status === 404) throw new Error('Assessment not found')
        throw new Error((await r.json()).detail || 'Failed to load')
      }
      const data = await r.json()
      setAssessment(data)
      setReportEdit(data.report ?? '')
    } catch (e) {
      setError(e.message)
      setAssessment(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAssessment()
  }, [id])

  const handleRunResearch = async () => {
    setActionLoading('research')
    setError(null)
    setResearchProgress([])
    setReportEdit('')
    setAssessment((prev) =>
      prev
        ? {
            ...prev,
            approach_document: null,
            report: null,
            quality_check: null,
            research_details: null,
          }
        : null
    )
    try {
      const r = await fetch(`${API}/assessment/${id}/research/stream`, { method: 'POST' })
      if (!r.ok) {
        const data = await r.json().catch(() => ({}))
        throw new Error(data.detail || 'Research failed')
      }
      const reader = r.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''
        for (const block of lines) {
          const dataLine = block.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue
          try {
            const jsonStr = dataLine.slice(6).trim()
            const { type, payload } = JSON.parse(jsonStr)
            setResearchProgress((prev) => [...prev, { type, payload }])
            if (type === 'done') {
              await loadAssessment()
            }
            if (type === 'error') {
              setError(payload?.message || 'Research failed')
            }
          } catch (_) {}
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  const handleRunQualityCheck = async () => {
    setActionLoading('qualityCheck')
    setError(null)
    try {
      const r = await fetch(`${API}/assessment/${id}/quality-check`, { method: 'POST' })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || 'Quality check failed')
      await loadAssessment()
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  const handleGenerateReport = async (opts = {}) => {
    setActionLoading('summarize')
    setError(null)
    setReportEdit('')
    setAssessment((prev) => (prev ? { ...prev, report: null, quality_check: null } : null))
    setClarificationQuestions([])
    setClarificationAnswers({})
    try {
      const body = opts.clarification_answers != null
        ? { clarification_answers: opts.clarification_answers }
        : opts.skip_clarification
          ? { skip_clarification: true }
          : undefined
      const r = await fetch(`${API}/assessment/${id}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || 'Summarize failed')
      if (data.status === 'needs_clarification' && Array.isArray(data.questions) && data.questions.length > 0) {
        setClarificationQuestions(data.questions)
        setError(null)
        setActionLoading(null)
        return
      }
      await loadAssessment()
    } catch (e) {
      setError(e.message)
      await loadAssessment()
    } finally {
      setActionLoading(null)
    }
  }

  const handleSubmitClarification = async () => {
    const answers = clarificationQuestions.map((_, i) => clarificationAnswers[i] ?? '')
    setActionLoading('summarize')
    setError(null)
    try {
      const r = await fetch(`${API}/assessment/${id}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clarification_questions: clarificationQuestions,
          clarification_answers: answers,
        }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || 'Summarize failed')
      if (data.status === 'needs_clarification' && Array.isArray(data.questions) && data.questions.length > 0) {
        setClarificationQuestions(data.questions)
        setClarificationAnswers({})
        return
      }
      setClarificationQuestions([])
      setClarificationAnswers({})
      await loadAssessment()
    } catch (e) {
      setError(e.message)
      await loadAssessment()
    } finally {
      setActionLoading(null)
    }
  }

  const handleGenerateAnyway = () => {
    handleGenerateReport({ skip_clarification: true })
  }

  const isValidationError = error && (
    /database migration|Data:.*required|mandatory/i.test(error) ||
    /contains database migration/i.test(error)
  )
  const handleQuickFixSaveAndRetry = async () => {
    const value = quickFixDbMigration || (profile.contains_database_migration || '').toLowerCase() || 'yes'
    if (!assessment?.profile || (value !== 'yes' && value !== 'no')) return
    setQuickFixLoading(true)
    setError(null)
    try {
      const updated = { ...assessment.profile, contains_database_migration: value }
      const r = await fetch(`${API}/assessment/${id}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      })
      if (!r.ok) throw new Error((await r.json()).detail || 'Save failed')
      await loadAssessment()
      setQuickFixDbMigration('')
      handleRunResearch()
    } catch (e) {
      setError(e.message)
    } finally {
      setQuickFixLoading(false)
    }
  }

  const handleSaveReport = async () => {
    setActionLoading('saveReport')
    setError(null)
    try {
      const r = await fetch(`${API}/assessment/${id}/report`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report: reportEdit }),
      })
      if (!r.ok) {
        const data = await r.json().catch(() => ({}))
        throw new Error(data.detail || 'Save failed')
      }
      await loadAssessment()
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  const handleDownloadDocx = () => {
    window.open(`${API}/assessment/${id}/report?format=docx`, '_blank', 'noopener')
  }

  if (loading && !assessment) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center text-slate-600">
        Loading assessment…
      </div>
    )
  }

  if (error && !assessment) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Link
          to="/admin"
          className="inline-block rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
        >
          Back to list
        </Link>
        <div className="mt-4 rounded-lg bg-red-50 p-4 text-red-800">{error}</div>
      </div>
    )
  }

  const profile = assessment?.profile || {}
  const status = assessment?.status ?? 'draft'
  const hasApproach = !!assessment?.approach_document
  const hasReport = !!(assessment?.report && assessment.report.trim())
  const qc = assessment?.quality_check

  const shortId = (id) => (id && id.length >= 8 ? id.slice(0, 8) : id) || '—'

  return (
    <div className="mx-auto max-w-4xl">
      {/* Dark header – match Admin Command Center wireframe */}
      <header className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 px-6 py-4 text-white">
        <div className="flex items-center gap-4">
          <Link
            to="/admin"
            className="rounded-lg border border-white/30 bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/20"
          >
            Back to list
          </Link>
          <div>
            <h1 className="text-xl font-bold">
              Admin Command Center · {profile.application_name || 'Unnamed'} ({shortId(assessment?.id)})
            </h1>
            <p className="mt-0.5 text-sm text-slate-400">
              Status: <span className="font-medium text-slate-200">{status}</span>
            </p>
          </div>
        </div>
      </header>

      <div className="px-4 py-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-200">
            {error}
            {isValidationError && assessment?.profile && (
              <div className="mt-4 rounded-lg border border-slate-500/50 bg-slate-800/50 p-4">
                <p className="mb-2 text-sm font-medium text-white">Fix missing data and retry</p>
                <div className="flex flex-wrap items-center gap-3">
                  <label className="text-sm text-slate-300">
                    Contains database migration:
                    <select
                      value={quickFixDbMigration || (profile.contains_database_migration || '').toLowerCase() || 'yes'}
                      onChange={(e) => setQuickFixDbMigration(e.target.value)}
                      className="ml-2 rounded border border-slate-500 bg-slate-700 px-2 py-1.5 text-white"
                    >
                      <option value="">Select…</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    onClick={handleQuickFixSaveAndRetry}
                    disabled={quickFixLoading}
                    className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {quickFixLoading ? 'Saving…' : 'Save and retry research'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Read-only profile */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Application profile</h2>
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
          <Section title="Overview">
            <Field label="Application" value={profile.application_name} />
            <Field label="Business purpose" value={profile.business_purpose} />
            <Field label="Description" value={profile.description} />
            <Field label="User count" value={profile.user_count_estimate} />
            <Field label="Priority" value={profile.priority} />
            <Field label="RTO" value={profile.rto} />
            <Field label="RPO" value={profile.rpo} />
            <Field label="Compliance" value={profile.compliance_requirements} />
            <Field label="Risks" value={profile.known_risks} />
          </Section>
          <Section title="Architecture">
            <Field label="Tech stack" value={profile.tech_stack} />
            <Field label="Current env" value={profile.current_environment} />
            <Field label="Target env" value={profile.target_environment} />
            <Field label="Current architecture" value={profile.current_architecture_description} />
            <Field label="Future architecture" value={profile.future_architecture_description} />
          </Section>
          <Section title="Data">
            <Field label="DB migration" value={profile.contains_database_migration} />
            <Field label="Data volume" value={profile.total_data_volume} />
            <Field label="DB types" value={profile.database_types} />
            <Field label="Ingestion" value={profile.data_ingestion} />
            <Field label="Ingress" value={profile.data_ingress} />
            <Field label="Egress" value={profile.data_egress} />
            <Field label="ETLs" value={profile.etl_pipelines} />
          </Section>
          <Section title="BC & DR / Cost / Security">
            <Field label="DR strategy" value={profile.current_dr_strategy} />
            <Field label="Backup" value={profile.backup_frequency} />
            <Field label="Auth" value={profile.authentication_type} />
            <Field label="Encryption at rest" value={profile.encryption_at_rest} />
            <Field label="Encryption in transit" value={profile.encryption_in_transit} />
            <Field label="Cost / Budget" value={profile.migration_budget} />
          </Section>
        </div>
        </section>

        {/* Actions: Run research, Generate report */}
        <section className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Research & report</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleRunResearch}
            disabled={actionLoading !== null || status === 'researching'}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
          >
            {actionLoading === 'research' ? 'Running research…' : 'Run research'}
          </button>
          <button
            onClick={() => handleGenerateReport()}
            disabled={actionLoading !== null || !hasApproach || status === 'summarizing'}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {actionLoading === 'summarize' ? 'Generating report…' : hasReport ? 'Regenerate report' : 'Generate report'}
          </button>
        </div>
          {!hasApproach && (
            <p className="mt-2 text-sm text-slate-500">Run research first to generate a report.</p>
          )}
          {/* Human-in-the-loop: diagram design asked for clarification */}
          {clarificationQuestions.length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="mb-2 font-medium text-amber-900">Architect: please clarify so we can generate an accurate diagram</p>
              <ul className="mb-3 space-y-3">
                {clarificationQuestions.map((q, i) => (
                  <li key={i}>
                    <label className="block text-sm font-medium text-slate-700">{i + 1}. {q}</label>
                    <input
                      type="text"
                      value={clarificationAnswers[i] ?? ''}
                      onChange={(e) => setClarificationAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
                      className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                      placeholder="Your answer (optional)"
                    />
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleSubmitClarification}
                  disabled={actionLoading !== null}
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {actionLoading === 'summarize' ? 'Submitting…' : 'Submit answers and generate report'}
                </button>
                <button
                  onClick={handleGenerateAnyway}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Generate anyway (use current design)
                </button>
              </div>
            </div>
          )}
          {/* Live research progress (SSE) – Cursor-style: thinking → retrieving → took Xs → key results → summarizing → done */}
          {researchProgress.length > 0 && (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Research progress (live)</p>
              <ul className="space-y-2 text-sm text-slate-700">
                {researchProgress.map((ev, i) => {
                  const duration = ev.payload?.duration_seconds != null ? ` (took ${ev.payload.duration_seconds}s)` : ''
                  let msg = ev.type
                  if (ev.payload?.message) msg = ev.payload.message
                  else if (ev.type === 'official_search_skipped' && ev.payload?.reason) msg = ev.payload.reason
                  else if (ev.type === 'key_results') {
                    msg = null
                    return (
                      <li key={i} className="rounded border border-emerald-200 bg-emerald-50/80 py-1.5 px-2">
                        <span className="font-medium text-emerald-800">{ev.payload?.message ?? 'Got key results'}</span>
                        {Array.isArray(ev.payload?.kb_sources) && ev.payload.kb_sources.length > 0 && (
                          <p className="mt-1 text-xs text-slate-600">KB: {ev.payload.kb_sources.join(', ')}</p>
                        )}
                        {Array.isArray(ev.payload?.official_titles) && ev.payload.official_titles.length > 0 && (
                          <p className="mt-0.5 text-xs text-slate-600">Official: {ev.payload.official_titles.join('; ')}</p>
                        )}
                      </li>
                    )
                  } else if (ev.type === 'kb_results') {
                    const count = ev.payload?.count ?? 0
                    const hits = ev.payload?.hits || []
                    msg = null
                    return (
                      <li key={i}>
                        <span className="font-medium">KB search: {count} hit(s){ev.payload?.duration_seconds != null ? ` (took ${ev.payload.duration_seconds}s)` : ''}</span>
                        {hits.length > 0 && (
                          <ul className="mt-1 ml-3 list-disc space-y-0.5 text-xs">
                            {hits.map((h, j) => (
                              <li key={j}>
                                <span className="font-mono">{h.file_path || '—'}</span> (score: {(h.score * 100).toFixed(0)}%) — {h.why_match || '—'}
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    )
                  } else if (ev.type === 'confidence' && ev.payload?.label) {
                    msg = `Confidence: ${ev.payload.label} (${Math.round((ev.payload.value ?? 0) * 100)}%)${duration}`
                  } else if (ev.type === 'official_search_results') {
                    const count = ev.payload?.count ?? 0
                    const results = ev.payload?.results || []
                    msg = null
                    return (
                      <li key={i}>
                        <span className="font-medium">Tavily (official docs): {count} result(s){ev.payload?.duration_seconds != null ? ` (took ${ev.payload.duration_seconds}s)` : ''}</span>
                        {results.length > 0 && (
                          <ul className="mt-1 ml-3 space-y-0.5 text-xs">
                            {results.map((r, j) => (
                              <li key={j}>
                                <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{r.title || r.url}</a>
                                {r.snippet_preview && <span className="block text-slate-500">{r.snippet_preview}…</span>}
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    )
                  } else if (ev.type === 'done') msg = ev.payload?.message ?? `Done${duration}`
                  else if (ev.type === 'error') msg = `Error: ${ev.payload?.message || 'Unknown'}`
                  if (msg === null) return null
                  const isStep = ev.payload?.step != null
                  return (
                    <li key={i} className={ev.type === 'official_search_skipped' ? 'text-amber-700' : isStep ? 'text-slate-800' : ''}>
                      {msg}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </section>

        {/* Document retrieval: what was returned from KB and Tavily (transparency) */}
        {assessment?.research_details && (assessment.research_details.kb_hits?.length > 0 || assessment.research_details.official_docs?.length > 0) && (
          <section className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Document retrieval (what was used for the approach)</h2>
            <p className="mb-4 text-sm text-slate-600">Sources retrieved from the knowledge base and from Tavily web search. The LLM used these to produce the approach document, aligned to migration pillars (architecture, data, security, BC/DR).</p>
            <div className="grid gap-6 md:grid-cols-2">
              {assessment.research_details.kb_hits?.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700">KB sources used</h3>
                  <ul className="space-y-2 text-sm">
                    {assessment.research_details.kb_hits.map((h, i) => (
                      <li key={i} className="rounded border border-slate-100 bg-white p-2">
                        <span className="font-mono text-xs text-slate-500">{h.file_path || '—'}</span>
                        <span className="ml-2 text-slate-600">score: {(Number(h.score) * 100).toFixed(0)}%</span>
                        {h.why_match && <p className="mt-1 text-xs text-slate-600">Why matched: {h.why_match}</p>}
                        {h.content_preview && <p className="mt-1 truncate text-xs text-slate-400" title={h.content_preview}>{h.content_preview.slice(0, 120)}…</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {assessment.research_details.official_docs?.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700">Retrieved from Tavily (official documentation)</h3>
                  <ul className="space-y-2 text-sm">
                    {assessment.research_details.official_docs.map((d, i) => (
                      <li key={i} className="rounded border border-slate-100 bg-white p-2">
                        <a href={d.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 hover:underline">{d.title || d.url}</a>
                        {d.snippet && <p className="mt-1 text-xs text-slate-600">{d.snippet.slice(0, 200)}{d.snippet.length > 200 ? '…' : ''}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Approach document */}
        {hasApproach && (
          <section className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Research (approach document)</h2>
          <pre className="max-h-64 overflow-auto rounded-lg bg-slate-100 p-4 text-xs text-slate-800 whitespace-pre-wrap">
            {assessment.approach_document}
          </pre>
          </section>
        )}

        {/* Quality check: comprehensive, actionable, useful, diagrams */}
        {(hasReport || reportEdit.trim()) && (
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Report quality check</h2>
            <p className="mb-3 text-sm text-slate-600">
              Ensures the report is comprehensive, actionable, useful, and includes a target-state architecture diagram. Run after generating or editing the report.
            </p>
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleRunQualityCheck}
                disabled={actionLoading !== null}
                className="rounded-lg border border-slate-300 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
              >
                {actionLoading === 'qualityCheck' ? 'Checking…' : qc ? 'Re-run quality check' : 'Run quality check'}
              </button>
            </div>
            {qc && (
              <div className={`rounded-lg border p-4 ${qc.overall_pass ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
                <p className="mb-3 font-medium text-slate-900">
                  {qc.overall_pass ? 'Report meets quality criteria' : 'Report could be improved'}
                </p>
                {/* Score-based explainability (new format) or legacy Yes/No */}
                <ul className="mb-3 space-y-2 text-sm">
                  {qc.comprehensive?.score != null ? (
                    <>
                      <li>
                        <span className="font-medium">Comprehensive (covers key areas):</span>{' '}
                        <span className={qc.comprehensive.score >= 60 ? 'text-emerald-700' : 'text-amber-700'}>{qc.comprehensive.score}/100</span>
                        <p className="mt-0.5 text-xs text-slate-600">{qc.comprehensive.reason}</p>
                      </li>
                      <li>
                        <span className="font-medium">Actionable (clear next steps):</span>{' '}
                        <span className={qc.actionable?.score >= 60 ? 'text-emerald-700' : 'text-amber-700'}>{qc.actionable?.score ?? '—'}/100</span>
                        <p className="mt-0.5 text-xs text-slate-600">{qc.actionable?.reason}</p>
                      </li>
                      <li>
                        <span className="font-medium">Useful (specific to this app):</span>{' '}
                        <span className={qc.useful?.score >= 60 ? 'text-emerald-700' : 'text-amber-700'}>{qc.useful?.score ?? '—'}/100</span>
                        <p className="mt-0.5 text-xs text-slate-600">{qc.useful?.reason}</p>
                      </li>
                      {qc.diagrams != null && (
                        <li>
                          <span className="font-medium">Diagrams (target-state architecture):</span>{' '}
                          <span className={qc.diagrams?.score >= 60 ? 'text-emerald-700' : 'text-amber-700'}>{qc.diagrams?.score ?? '—'}/100</span>
                          <p className="mt-0.5 text-xs text-slate-600">{qc.diagrams?.reason}</p>
                        </li>
                      )}
                    </>
                  ) : (
                    <>
                      <li>Comprehensive: {qc.comprehensive_ok ? 'Yes' : 'No'}</li>
                      <li>Actionable: {qc.actionable_ok ? 'Yes' : 'No'}</li>
                      <li>Useful: {qc.useful_ok ? 'Yes' : 'No'}</li>
                    </>
                  )}
                </ul>
                {qc.suggestions && qc.suggestions.length > 0 && (
                  <>
                    <p className="text-sm font-medium text-slate-700">Suggestions:</p>
                    <ul className="list-inside list-disc text-sm text-slate-600">
                      {qc.suggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </section>
        )}

        {/* Report: view / edit / save / download */}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Report</h2>
        {!hasReport && !reportEdit.trim() ? (
          <p className="text-sm text-slate-500">No report yet. Generate report above.</p>
        ) : (
          <>
            <textarea
              value={reportEdit}
              onChange={(e) => setReportEdit(e.target.value)}
              className="mb-3 w-full min-h-[280px] rounded-lg border border-slate-300 p-3 font-mono text-sm text-slate-800"
              placeholder="Report content (markdown or plain text)"
              spellCheck="false"
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleSaveReport}
                disabled={actionLoading !== null}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                {actionLoading === 'saveReport' ? 'Saving…' : 'Save edits'}
              </button>
              <button
                onClick={handleDownloadDocx}
                disabled={!reportEdit.trim()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Download DOCX
              </button>
              <span className="text-slate-400">|</span>
              <span className="text-sm text-slate-600">Target diagram:</span>
              <a
                href={`${API}/assessment/${id}/diagram/target?format=png`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Download PNG
              </a>
              <a
                href={`${API}/assessment/${id}/diagram/target?format=mmd`}
                target="_blank"
                rel="noopener noreferrer"
                download="target_architecture.mmd"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Download .mmd (editable)
              </a>
            </div>
          </>
        )}
        </section>
      </div>
    </div>
  )
}
