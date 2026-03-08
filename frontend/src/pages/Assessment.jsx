import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'

const API = '/api'

const PILLARS = [
  { id: 'overview', label: 'Overview' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'data', label: 'Data' },
  { id: 'bc-dr', label: 'BC & DR' },
  { id: 'cost', label: 'Cost' },
  { id: 'security', label: 'Security' },
  { id: 'project', label: 'Project' },
]

const PILLAR_ORDER = PILLARS.map((p) => p.id)

function getNextPillar(current) {
  const idx = PILLAR_ORDER.indexOf(current)
  return idx >= 0 && idx < PILLAR_ORDER.length - 1 ? PILLAR_ORDER[idx + 1] : null
}

const defaultProfile = {
  application_name: '',
  business_purpose: '',
  description: '',
  user_count_estimate: '',
  priority: 'medium',
  rto: '',
  rpo: '',
  contains_database_migration: '',
  compliance_requirements: [],
  known_risks: '',
  constraints: '',
  additional_notes: '',
  tech_stack: [],
  current_environment: 'on-prem',
  target_environment: 'azure',
  current_architecture_description: '',
  current_architecture_diagram_path: null,
  future_architecture_description: '',
  future_architecture_diagram_path: null,
  total_data_volume: '',
  database_types: [],
  current_databases_description: '',
  target_databases_description: '',
  data_retention_requirements: '',
  data_migration_notes: '',
  data_ingestion: '',
  data_ingress: '',
  data_egress: '',
  etl_pipelines: '',
  current_dr_strategy: '',
  backup_frequency: '',
  failover_approach: '',
  dr_testing_frequency: '',
  bc_dr_notes: '',
  current_annual_cost: '',
  migration_budget: '',
  cost_constraints: '',
  licensing_considerations: '',
  authentication_type: '',
  encryption_at_rest: '',
  encryption_in_transit: '',
  pii_handling: '',
  compliance_frameworks: [],
  project_manager: '',
  timeline_expectation: '',
  team_size: '',
  dependencies: [],
  integrations: [],
  preferred_go_live: '',
}

function parseList(s) {
  return s ? s.split(/[,;]/).map((x) => x.trim()).filter(Boolean) : []
}

function hasSubstance(str, minLen = 3) {
  const s = (str || '').trim()
  return s.length >= minLen && !/^(n\/a|tbd|none|-|na)$/i.test(s)
}
function isYesNo(s) {
  const v = (s || '').trim().toLowerCase()
  return v === 'yes' || v === 'no' || v === 'y' || v === 'n'
}

// Per-pillar validation (must match backend). Returns { errors, hints, invalidFields }.
function validateOverview(profile) {
  const errors = []
  const hints = []
  const invalidFields = []
  if (!(profile.application_name || '').trim()) { errors.push('Application name is required.'); invalidFields.push('application_name') }
  if (!hasSubstance(profile.business_purpose)) { errors.push('Business purpose is required (at least a brief description).'); invalidFields.push('business_purpose') }
  if (!(profile.user_count_estimate || '').trim()) { errors.push('User count (estimate) is required.'); hints.push('Use a number or range, e.g. 1000, 10K-50K.'); invalidFields.push('user_count_estimate') }
  if (!(profile.priority || '').trim()) { errors.push('Priority is required.'); invalidFields.push('priority') }
  if (!(profile.rto || '').trim()) { errors.push('RTO (Recovery Time Objective) is required.'); hints.push('If your application is critical, a typical RTO is 1 hour. For high priority, 4 hours is common.'); invalidFields.push('rto') }
  if (!(profile.rpo || '').trim()) { errors.push('RPO (Recovery Point Objective) is required.'); hints.push('Typical RPO for critical apps: 1 hour or less. For high priority, 4–24 hours.'); invalidFields.push('rpo') }
  return { errors, hints, invalidFields }
}

function validateArchitecture(profile, listInputs) {
  const errors = []
  const hints = []
  const invalidFields = []
  const ts = parseList(listInputs.tech_stack || '')
  if (ts.length < 1) { errors.push('Tech stack is required (at least one technology).'); invalidFields.push('tech_stack') }
  if (!(profile.current_environment || '').trim()) { errors.push('Current environment is required.'); invalidFields.push('current_environment') }
  if (!(profile.target_environment || '').trim()) { errors.push('Target environment is required.'); invalidFields.push('target_environment') }
  const hasDesc = hasSubstance(profile.current_architecture_description, 2)
  const hasDiagram = !!(profile.current_architecture_diagram_path && profile.current_architecture_diagram_path.trim())
  if (!hasDesc && !hasDiagram) {
    errors.push('Current state: provide either architecture description or upload a diagram.')
    hints.push('Describe the main components (e.g. web tier, app server, database) or upload an architecture diagram.')
    invalidFields.push('current_architecture_description', 'current_architecture_diagram_path')
  }
  if (!hasSubstance(profile.future_architecture_description, 2) && !(profile.future_architecture_diagram_path && profile.future_architecture_diagram_path.trim())) {
    hints.push('Target state: if not yet defined, add a short note (e.g. "To be determined" or desired outcome) to improve the assessment.')
  }
  return { errors, hints, invalidFields }
}

function validateData(profile, listInputs) {
  const errors = []
  const hints = []
  const invalidFields = []
  if (!isYesNo(profile.contains_database_migration)) {
    errors.push('Please answer whether this application contains database migration (Yes/No).')
    hints.push('Select Yes if you will migrate or replicate databases as part of this move.')
    invalidFields.push('contains_database_migration')
  } else if (['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase())) {
    if (!hasSubstance(profile.total_data_volume, 2)) { errors.push('Total data volume is required when database migration is Yes.'); hints.push('e.g. 500 GB, 2 TB.'); invalidFields.push('total_data_volume') }
    if (parseList(listInputs.database_types || '').length < 1) { errors.push('At least one database type is required when database migration is Yes.'); invalidFields.push('database_types') }
    if (!hasSubstance(profile.current_databases_description, 2)) { errors.push('Current databases description is required when database migration is Yes.'); invalidFields.push('current_databases_description') }
  }
  return { errors, hints, invalidFields }
}

function validateBcDr(profile) {
  const errors = []
  const invalidFields = []
  if (!hasSubstance(profile.current_dr_strategy)) { errors.push('Current DR strategy is required.'); invalidFields.push('current_dr_strategy') }
  if (!(profile.backup_frequency || '').trim()) { errors.push('Backup frequency is required.'); invalidFields.push('backup_frequency') }
  if (!(profile.failover_approach || '').trim()) { errors.push('Failover approach is required.'); invalidFields.push('failover_approach') }
  if (!(profile.dr_testing_frequency || '').trim()) { errors.push('DR testing frequency is required.'); invalidFields.push('dr_testing_frequency') }
  return { errors, hints: [], invalidFields }
}

function validateSecurity(profile) {
  const errors = []
  const invalidFields = []
  if (!(profile.authentication_type || '').trim()) { errors.push('Authentication type is required.'); invalidFields.push('authentication_type') }
  if (!(profile.encryption_at_rest || '').trim()) { errors.push('Encryption at rest is required.'); invalidFields.push('encryption_at_rest') }
  if (!(profile.encryption_in_transit || '').trim()) { errors.push('Encryption in transit is required.'); invalidFields.push('encryption_in_transit') }
  return { errors, hints: [], invalidFields }
}

// Full profile validation for "Submit for assessment" (all pillars)
function validateFullProfile(profile, listInputs) {
  const o = validateOverview(profile)
  const a = validateArchitecture(profile, listInputs)
  const d = validateData(profile, listInputs)
  const b = validateBcDr(profile)
  const s = validateSecurity(profile)
  return {
    errors: [...o.errors, ...a.errors, ...d.errors, ...b.errors, ...s.errors],
    hints: [...o.hints, ...a.hints, ...d.hints, ...b.hints, ...s.hints],
    invalidFields: [...(o.invalidFields || []), ...(a.invalidFields || []), ...(d.invalidFields || []), ...(b.invalidFields || []), ...(s.invalidFields || [])],
  }
}

function getPillarValidation(activePillar, profile, listInputs) {
  const out = { errors: [], hints: [], invalidFields: [] }
  switch (activePillar) {
    case 'overview': return validateOverview(profile)
    case 'architecture': return validateArchitecture(profile, listInputs)
    case 'data': return validateData(profile, listInputs)
    case 'bc-dr': return validateBcDr(profile)
    case 'security': return validateSecurity(profile)
    default: return out
  }
}

const req = <span className="text-slate-600"> *</span>
const opt = <span className="text-slate-400 font-normal"> (optional)</span>

export default function Assessment() {
  const { id: routeId } = useParams()
  const [assessmentId, setAssessmentId] = useState(routeId || null)
  const [step, setStep] = useState(1)
  const [profile, setProfile] = useState(defaultProfile)
  const [approachDoc, setApproachDoc] = useState(null)
  const [report, setReport] = useState(null)
  const [status, setStatus] = useState('draft')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activePillar, setActivePillar] = useState('overview')
  const [listInputs, setListInputs] = useState({
    compliance_requirements: '',
    tech_stack: '',
    database_types: '',
    dependencies: '',
    integrations: '',
    compliance_frameworks: '',
  })
  const [uploadingDiagram, setUploadingDiagram] = useState(null)
  const [validation, setValidation] = useState(null)
  const [invalidFields, setInvalidFields] = useState([])
  const [analysisPhase, setAnalysisPhase] = useState('idle') // 'idle' | 'analyzing' | 'review' | 'running'
  const [analysisSteps, setAnalysisSteps] = useState([])
  const [analysisFindings, setAnalysisFindings] = useState({ findings: [], warnings: [] })

  useEffect(() => {
    if (routeId) {
      setAssessmentId(routeId)
    } else if (!assessmentId) {
      fetch(`${API}/assessment/start`, { method: 'POST' })
        .then((r) => r.json())
        .then((d) => setAssessmentId(d.assessment_id))
        .catch((e) => setError(e.message))
    }
  }, [routeId])

  useEffect(() => {
    if (assessmentId) {
      fetch(`${API}/assessment/${assessmentId}`)
        .then((r) => r.json())
        .then((d) => {
          if (d.profile) {
            const p = { ...defaultProfile, ...d.profile }
            setProfile(p)
            setListInputs({
              compliance_requirements: (p.compliance_requirements || []).join(', '),
              tech_stack: (p.tech_stack || []).join(', '),
              database_types: (p.database_types || []).join(', '),
              dependencies: (p.dependencies || []).join(', '),
              integrations: (p.integrations || []).join(', '),
              compliance_frameworks: (p.compliance_frameworks || []).join(', '),
            })
          }
          setApproachDoc(d.approach_document)
          setReport(d.report)
          setStatus(d.status)
          // Application User flow: only step 1 (Profile) and step 2 (Submit / Confirmation)
          if (d.status === 'submitted') setStep(2)
          else if (d.approach_document) setStep(2)
          else setStep(1)
        })
        .catch(() => {})
    }
  }, [assessmentId, status])

  // Fetch validation when on Submit step (profile must be saved)
  useEffect(() => {
    if (step === 2 && assessmentId && status !== 'submitted') {
      fetch(`${API}/assessment/${assessmentId}/validate`)
        .then((r) => r.json())
        .then((v) => setValidation(v))
        .catch(() => setValidation({ valid: false, errors: ['Could not validate. Please refresh or go back to profile.'], warnings: [], suggestions: [] }))
    } else if (status === 'submitted') {
      setValidation({ valid: true })
    } else {
      setValidation(null)
    }
  }, [step, assessmentId, status])

  const handleContinueToNextPillar = () => {
    const next = getNextPillar(activePillar)
    if (!next) return
    setError(null)
    const p = {
      ...profile,
      tech_stack: parseList(listInputs.tech_stack),
      database_types: parseList(listInputs.database_types),
    }
    const listForValidation = { ...listInputs, tech_stack: listInputs.tech_stack, database_types: listInputs.database_types }
    const { errors, hints, invalidFields: invalid } = getPillarValidation(activePillar, p, listForValidation)
    if (errors.length > 0) {
      setInvalidFields(invalid || [])
      setError([...errors, ...hints.filter((h) => h)].join(' '))
      return
    }
    setInvalidFields([])
    setActivePillar(next)
  }

  const handleSaveProfile = (e) => {
    e.preventDefault()
    setError(null)
    const p = {
      ...profile,
      compliance_requirements: parseList(listInputs.compliance_requirements),
      tech_stack: parseList(listInputs.tech_stack),
      database_types: parseList(listInputs.database_types),
      dependencies: parseList(listInputs.dependencies),
      integrations: parseList(listInputs.integrations),
      compliance_frameworks: parseList(listInputs.compliance_frameworks),
    }
    const { errors, hints, invalidFields: invalid } = validateFullProfile(p, listInputs)
    if (errors.length > 0) {
      setInvalidFields(invalid || [])
      const parts = [...errors]
      if (hints.length) parts.push('— ' + hints.join(' '))
      setError(parts.join(' '))
      return
    }
    setInvalidFields([])
    setLoading(true)
    fetch(`${API}/assessment/${assessmentId}/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(p),
    })
      .then(async (r) => {
        if (!r.ok) {
          const d = await r.json().catch(() => ({}))
          throw new Error(d.detail || 'Failed')
        }
        setStep(2)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const handleDiagramUpload = async (type, file) => {
    if (!file || !assessmentId) return
    setUploadingDiagram(type)
    const form = new FormData()
    form.append('type', type)
    form.append('file', file)
    try {
      const r = await fetch(`${API}/assessment/${assessmentId}/upload/diagram`, {
        method: 'POST',
        body: form,
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || 'Upload failed')
      setProfile((prev) => ({
        ...prev,
        [type === 'current' ? 'current_architecture_diagram_path' : 'future_architecture_diagram_path']: d.path,
      }))
      if (type === 'current') {
        setInvalidFields((prev) => prev.filter((f) => f !== 'current_architecture_diagram_path' && f !== 'current_architecture_description'))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setUploadingDiagram(null)
    }
  }

  // Submit for assessment (Application User) – no research
  const submitRequest = () => {
    setError(null)
    setLoading(true)
    fetch(`${API}/assessment/${assessmentId}/submit`, { method: 'POST' })
      .then(async (r) => {
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.detail || 'Submit failed')
        return d
      })
      .then((d) => {
        setStatus(d.status || 'submitted')
        setAnalysisPhase('idle')
        setAnalysisSteps([])
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const handleSubmitClick = () => {
    if (analysisPhase === 'review') {
      setAnalysisPhase('running')
      setAnalysisSteps((prev) => [
        ...prev.map((s) => ({ ...s, status: 'done' })),
        { label: 'Submitting...', status: 'active' },
      ])
      submitRequest()
      return
    }
    setError(null)
    setAnalysisPhase('analyzing')
    setAnalysisSteps([
      { label: 'Analyzing your input...', status: 'active' },
      { label: 'Checking data reasonableness...', status: 'pending' },
      { label: 'Reviewing findings...', status: 'pending' },
    ])
    const t1 = setTimeout(() => {
      setAnalysisSteps((prev) =>
        prev.map((s, i) => ({
          ...s,
          status: i === 0 ? 'done' : i === 1 ? 'active' : 'pending',
        }))
      )
    }, 500)
    const t2 = setTimeout(() => {
      setAnalysisSteps((prev) =>
        prev.map((s, i) => ({
          ...s,
          status: i <= 1 ? 'done' : 'active',
        }))
      )
    }, 1000)
    fetch(`${API}/assessment/${assessmentId}/validate`)
      .then((r) => r.json())
      .then((data) => {
        clearTimeout(t1)
        clearTimeout(t2)
        setAnalysisSteps((prev) =>
          prev.map((s) => ({ ...s, status: 'done' }))
        )
        setValidation(data)
        if (!data.valid) {
          setAnalysisPhase('idle')
          return
        }
        const findings = data.findings || []
        const warnings = data.warnings || []
        if (findings.length > 0 || warnings.length > 0) {
          setAnalysisFindings({ findings, warnings })
          setAnalysisPhase('review')
        } else {
          setAnalysisPhase('running')
          setAnalysisSteps((prev) => [
            ...prev,
            { label: 'Submitting...', status: 'active' },
          ])
          submitRequest()
        }
      })
      .catch((e) => {
        setError(e.message || 'Analysis failed')
        setAnalysisPhase('idle')
        setAnalysisSteps([])
      })
  }

  const handleConfirmAndSubmit = () => {
    setAnalysisPhase('running')
    setAnalysisSteps((prev) => [
      ...prev.map((s) => ({ ...s, status: 'done' })),
      { label: 'Submitting...', status: 'active' },
    ])
    submitRequest()
  }

  const handleRunSummarize = () => {
    setError(null)
    setLoading(true)
    fetch(`${API}/assessment/${assessmentId}/summarize`, { method: 'POST' })
      .then(async (r) => {
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.detail || 'Summarize failed')
        return d
      })
      .then((d) => {
        setReport(d.report)
        setStatus('done')
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  if (!assessmentId) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-slate-600">Starting assessment…</p>
      </div>
    )
  }

  const steps = [
    { n: 1, label: 'Profile', done: step > 1 },
    { n: 2, label: 'Submit', done: status === 'submitted' },
  ]

  const inputClass = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900'
  const labelClass = 'block text-sm font-medium text-slate-700'
  const sectionClass = 'space-y-4'
  const fieldInvalid = (name) => invalidFields.includes(name)
  const inputClassFor = (name) => `${inputClass} ${fieldInvalid(name) ? 'border-red-500 ring-1 ring-red-500' : ''}`
  const labelClassFor = (name) => `${labelClass} ${fieldInvalid(name) ? 'text-red-600' : ''}`
  const RequiredMsg = ({ name }) => (fieldInvalid(name) ? <p className="mt-1 text-sm text-red-600">Required</p> : null)
  const clearInvalid = (name) => setInvalidFields((prev) => prev.filter((f) => f !== name))

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Application Assessment</h1>
      <p className="mt-1 text-slate-600">Submit your migration request: complete the profile, then submit for assessment. Admins will run research and produce the report.</p>

      <div className="mt-8 flex gap-2">
        {steps.map((s) => (
          <div
            key={s.n}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              step === s.n ? 'bg-emerald-600 text-white' : s.done ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
            }`}
          >
            {s.n}. {s.label}
          </div>
        ))}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          {error}
        </div>
      )}

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {step === 1 && (
          <form onSubmit={handleSaveProfile}>
            <p className="mb-4 text-sm text-slate-600">
              Fill in required fields, then Submit for assessment. Use tabs to switch sections.
            </p>
            <div className="mb-6 flex flex-wrap gap-2 border-b border-slate-200 pb-2">
              {PILLARS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setActivePillar(p.id)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                    activePillar === p.id ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {activePillar === 'overview' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">1. General Overview</h2>
                <div>
                  <label className={labelClassFor('application_name')}>Application name{req}</label>
                  <input
                    type="text"
                    required
                    value={profile.application_name}
                    onChange={(e) => { clearInvalid('application_name'); setProfile((p) => ({ ...p, application_name: e.target.value })) }}
                    className={inputClassFor('application_name')}
                    placeholder="e.g. OrderService"
                  />
                  <RequiredMsg name="application_name" />
                </div>
                <div>
                  <label className={labelClassFor('business_purpose')}>Business purpose / What business it does{req}</label>
                  <textarea
                    rows={2}
                    value={profile.business_purpose}
                    onChange={(e) => { clearInvalid('business_purpose'); setProfile((p) => ({ ...p, business_purpose: e.target.value })) }}
                    className={inputClassFor('business_purpose')}
                    placeholder="e.g. Order processing and inventory management"
                  />
                  <RequiredMsg name="business_purpose" />
                </div>
                <div>
                  <label className={labelClass}>Description{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.description}
                    onChange={(e) => setProfile((p) => ({ ...p, description: e.target.value }))}
                    className={inputClass}
                    placeholder="Brief description"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClassFor('user_count_estimate')}>User count (estimate){req}</label>
                    <input
                      type="text"
                      value={profile.user_count_estimate}
                      onChange={(e) => { clearInvalid('user_count_estimate'); setProfile((p) => ({ ...p, user_count_estimate: e.target.value })) }}
                      className={inputClassFor('user_count_estimate')}
                      placeholder="e.g. 1000, 10K-50K"
                    />
                    <RequiredMsg name="user_count_estimate" />
                  </div>
                  <div>
                    <label className={labelClassFor('priority')}>Priority{req}</label>
                    <select
                      value={profile.priority}
                      onChange={(e) => { clearInvalid('priority'); setProfile((p) => ({ ...p, priority: e.target.value })) }}
                      className={inputClassFor('priority')}
                    >
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                    <RequiredMsg name="priority" />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClassFor('rto')}>RTO (Recovery Time Objective){req}</label>
                    <input
                      type="text"
                      value={profile.rto}
                      onChange={(e) => { clearInvalid('rto'); setProfile((p) => ({ ...p, rto: e.target.value })) }}
                      className={inputClassFor('rto')}
                      placeholder="e.g. 4 hours"
                    />
                    <RequiredMsg name="rto" />
                  </div>
                  <div>
                    <label className={labelClassFor('rpo')}>RPO (Recovery Point Objective){req}</label>
                    <input
                      type="text"
                      value={profile.rpo}
                      onChange={(e) => { clearInvalid('rpo'); setProfile((p) => ({ ...p, rpo: e.target.value })) }}
                      className={inputClassFor('rpo')}
                      placeholder="e.g. 1 hour"
                    />
                    <RequiredMsg name="rpo" />
                  </div>
                </div>
                <p className="text-sm text-slate-500">
                  Hint: If your application is critical, a typical RTO is 1 hour; for high priority, 4 hours is common. RPO for critical apps is often 1 hour or less.
                </p>
                <div>
                  <label className={labelClass}>Compliance requirements (comma-separated){opt}</label>
                  <input
                    type="text"
                    value={listInputs.compliance_requirements}
                    onChange={(e) => setListInputs((l) => ({ ...l, compliance_requirements: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. PCI, HIPAA, SOC2"
                  />
                </div>
                <div>
                  <label className={labelClass}>Known risks{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.known_risks}
                    onChange={(e) => setProfile((p) => ({ ...p, known_risks: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Constraints{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.constraints}
                    onChange={(e) => setProfile((p) => ({ ...p, constraints: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Additional notes{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.additional_notes}
                    onChange={(e) => setProfile((p) => ({ ...p, additional_notes: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            )}

            {activePillar === 'architecture' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">2. Architecture</h2>
                <div>
                  <label className={labelClassFor('tech_stack')}>Tech stack (comma-separated){req}</label>
                  <input
                    type="text"
                    value={listInputs.tech_stack}
                    onChange={(e) => { clearInvalid('tech_stack'); setListInputs((l) => ({ ...l, tech_stack: e.target.value })) }}
                    className={inputClassFor('tech_stack')}
                    placeholder="e.g. Java 11, Spring Boot, Oracle DB"
                  />
                  <RequiredMsg name="tech_stack" />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClassFor('current_environment')}>Current environment{req}</label>
                    <select
                      value={profile.current_environment}
                      onChange={(e) => { clearInvalid('current_environment'); setProfile((p) => ({ ...p, current_environment: e.target.value })) }}
                      className={inputClassFor('current_environment')}
                    >
                      <option value="on-prem">On-premises</option>
                      <option value="vm">Virtual machines</option>
                      <option value="cloud-legacy">Cloud (legacy)</option>
                      <option value="other">Other</option>
                    </select>
                    <RequiredMsg name="current_environment" />
                  </div>
                  <div>
                    <label className={labelClassFor('target_environment')}>Target environment{req}</label>
                    <select
                      value={profile.target_environment}
                      onChange={(e) => { clearInvalid('target_environment'); setProfile((p) => ({ ...p, target_environment: e.target.value })) }}
                      className={inputClassFor('target_environment')}
                    >
                      <option value="azure">Azure</option>
                      <option value="aws">AWS</option>
                      <option value="gcp">GCP</option>
                      <option value="other">Other</option>
                    </select>
                    <RequiredMsg name="target_environment" />
                  </div>
                </div>
                <p className="text-sm text-slate-600">Provide either a description or a diagram of your current architecture (one required).</p>
                <div>
                  <label className={labelClassFor('current_architecture_description')}>Current state architecture description{opt}</label>
                  <textarea
                    rows={3}
                    value={profile.current_architecture_description}
                    onChange={(e) => { clearInvalid('current_architecture_description'); clearInvalid('current_architecture_diagram_path'); setProfile((p) => ({ ...p, current_architecture_description: e.target.value })) }}
                    className={inputClassFor('current_architecture_description')}
                    placeholder="Describe current architecture (e.g. three-tier: web, app, DB)"
                  />
                  <RequiredMsg name="current_architecture_description" />
                </div>
                <div>
                  <label className={labelClassFor('current_architecture_diagram_path')}>Current state diagram (PNG, JPG){opt}</label>
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) handleDiagramUpload('current', f)
                    }}
                    className="mt-1 text-sm"
                  />
                  {uploadingDiagram === 'current' && <span className="ml-2 text-sm text-slate-500">Uploading…</span>}
                  {profile.current_architecture_diagram_path && (
                    <p className="mt-1 text-sm text-emerald-600">Uploaded</p>
                  )}
                  <RequiredMsg name="current_architecture_diagram_path" />
                </div>
                <div>
                  <label className={labelClass}>Future state architecture description{opt}</label>
                  <textarea
                    rows={3}
                    value={profile.future_architecture_description}
                    onChange={(e) => setProfile((p) => ({ ...p, future_architecture_description: e.target.value }))}
                    className={inputClass}
                    placeholder="Describe target architecture if known, or e.g. To be determined"
                  />
                  <p className="mt-1 text-sm text-slate-500">If you don&apos;t have a target state yet, add a short note (e.g. &quot;To be determined&quot;) to improve the assessment.</p>
                </div>
                <div>
                  <label className={labelClass}>Future state diagram (PNG, JPG){opt}</label>
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) handleDiagramUpload('future', f)
                    }}
                    className="mt-1 text-sm"
                  />
                  {uploadingDiagram === 'future' && <span className="ml-2 text-sm text-slate-500">Uploading…</span>}
                  {profile.future_architecture_diagram_path && (
                    <p className="mt-1 text-sm text-emerald-600">Uploaded</p>
                  )}
                </div>
              </div>
            )}

            {activePillar === 'data' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">3. Data Management</h2>
                <div>
                  <label className={labelClassFor('contains_database_migration')}>Does this application contain database migration?{req}</label>
                  <select
                    value={profile.contains_database_migration}
                    onChange={(e) => { clearInvalid('contains_database_migration'); setProfile((p) => ({ ...p, contains_database_migration: e.target.value })) }}
                    className={inputClassFor('contains_database_migration')}
                  >
                    <option value="">Select Yes or No</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                  <p className="mt-1 text-sm text-slate-500">Select Yes if you will migrate or replicate databases as part of this move.</p>
                  <RequiredMsg name="contains_database_migration" />
                </div>
                <div>
                  <label className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? labelClassFor('total_data_volume') : labelClass}>
                    Total data volume{['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? req : opt}
                  </label>
                  <input
                    type="text"
                    value={profile.total_data_volume}
                    onChange={(e) => { clearInvalid('total_data_volume'); setProfile((p) => ({ ...p, total_data_volume: e.target.value })) }}
                    className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? inputClassFor('total_data_volume') : inputClass}
                    placeholder="e.g. 500 GB, 2 TB"
                  />
                  <RequiredMsg name="total_data_volume" />
                </div>
                <div>
                  <label className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? labelClassFor('database_types') : labelClass}>
                    Database types (comma-separated){['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? req : opt}
                  </label>
                  <input
                    type="text"
                    value={listInputs.database_types}
                    onChange={(e) => { clearInvalid('database_types'); setListInputs((l) => ({ ...l, database_types: e.target.value })) }}
                    className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? inputClassFor('database_types') : inputClass}
                    placeholder="e.g. Oracle, SQL Server, PostgreSQL"
                  />
                  <RequiredMsg name="database_types" />
                </div>
                <div>
                  <label className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? labelClassFor('current_databases_description') : labelClass}>
                    Current databases (description){['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? req : opt}
                  </label>
                  <textarea
                    rows={2}
                    value={profile.current_databases_description}
                    onChange={(e) => { clearInvalid('current_databases_description'); setProfile((p) => ({ ...p, current_databases_description: e.target.value })) }}
                    className={['yes', 'y'].includes((profile.contains_database_migration || '').trim().toLowerCase()) ? inputClassFor('current_databases_description') : inputClass}
                    placeholder="DBs, sizes, versions"
                  />
                  <RequiredMsg name="current_databases_description" />
                </div>
                <div>
                  <label className={labelClass}>Target databases (if known){opt}</label>
                  <textarea
                    rows={2}
                    value={profile.target_databases_description}
                    onChange={(e) => setProfile((p) => ({ ...p, target_databases_description: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Data retention requirements{opt}</label>
                  <input
                    type="text"
                    value={profile.data_retention_requirements}
                    onChange={(e) => setProfile((p) => ({ ...p, data_retention_requirements: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. 7 years for compliance"
                  />
                </div>
                <div>
                  <label className={labelClass}>Data ingestion{opt}</label>
                  <input
                    type="text"
                    value={profile.data_ingestion}
                    onChange={(e) => setProfile((p) => ({ ...p, data_ingestion: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. batch, real-time, streaming, APIs, file drops"
                  />
                </div>
                <div>
                  <label className={labelClass}>Ingress (sources, formats, volume){opt}</label>
                  <textarea
                    rows={2}
                    value={profile.data_ingress}
                    onChange={(e) => setProfile((p) => ({ ...p, data_ingress: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. API from OrderSys, Kafka 10K msg/day"
                  />
                </div>
                <div>
                  <label className={labelClass}>Egress (destinations, formats){opt}</label>
                  <textarea
                    rows={2}
                    value={profile.data_egress}
                    onChange={(e) => setProfile((p) => ({ ...p, data_egress: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. data warehouse, reports, 3rd party APIs"
                  />
                </div>
                <div>
                  <label className={labelClass}>ETL pipelines (if any){opt}</label>
                  <textarea
                    rows={2}
                    value={profile.etl_pipelines}
                    onChange={(e) => setProfile((p) => ({ ...p, etl_pipelines: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. SSIS daily, Informatica hourly"
                  />
                </div>
                <div>
                  <label className={labelClass}>Data migration notes{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.data_migration_notes}
                    onChange={(e) => setProfile((p) => ({ ...p, data_migration_notes: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            )}

            {activePillar === 'bc-dr' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">4. Business Continuity & DR</h2>
                <div>
                  <label className={labelClassFor('current_dr_strategy')}>Current DR strategy{req}</label>
                  <textarea
                    rows={2}
                    value={profile.current_dr_strategy}
                    onChange={(e) => { clearInvalid('current_dr_strategy'); setProfile((p) => ({ ...p, current_dr_strategy: e.target.value })) }}
                    className={inputClassFor('current_dr_strategy')}
                    placeholder="e.g. Backup to tape, no replication"
                  />
                  <RequiredMsg name="current_dr_strategy" />
                </div>
                <div>
                  <label className={labelClassFor('backup_frequency')}>Backup frequency{req}</label>
                  <input
                    type="text"
                    value={profile.backup_frequency}
                    onChange={(e) => { clearInvalid('backup_frequency'); setProfile((p) => ({ ...p, backup_frequency: e.target.value })) }}
                    className={inputClassFor('backup_frequency')}
                    placeholder="e.g. daily, weekly"
                  />
                  <RequiredMsg name="backup_frequency" />
                </div>
                <div>
                  <label className={labelClassFor('failover_approach')}>Failover approach{req}</label>
                  <input
                    type="text"
                    value={profile.failover_approach}
                    onChange={(e) => { clearInvalid('failover_approach'); setProfile((p) => ({ ...p, failover_approach: e.target.value })) }}
                    className={inputClassFor('failover_approach')}
                    placeholder="e.g. Manual failover, cold standby"
                  />
                  <RequiredMsg name="failover_approach" />
                </div>
                <div>
                  <label className={labelClassFor('dr_testing_frequency')}>DR testing frequency{req}</label>
                  <input
                    type="text"
                    value={profile.dr_testing_frequency}
                    onChange={(e) => { clearInvalid('dr_testing_frequency'); setProfile((p) => ({ ...p, dr_testing_frequency: e.target.value })) }}
                    className={inputClassFor('dr_testing_frequency')}
                    placeholder="e.g. quarterly"
                  />
                  <RequiredMsg name="dr_testing_frequency" />
                </div>
                <div>
                  <label className={labelClass}>BC/DR additional notes{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.bc_dr_notes}
                    onChange={(e) => setProfile((p) => ({ ...p, bc_dr_notes: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            )}

            {activePillar === 'cost' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">5. Cost</h2>
                <div>
                  <label className={labelClass}>Current annual cost (infra, ops){opt}</label>
                  <input
                    type="text"
                    value={profile.current_annual_cost}
                    onChange={(e) => setProfile((p) => ({ ...p, current_annual_cost: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. $50K/year"
                  />
                </div>
                <div>
                  <label className={labelClass}>Migration budget{opt}</label>
                  <input
                    type="text"
                    value={profile.migration_budget}
                    onChange={(e) => setProfile((p) => ({ ...p, migration_budget: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. $100K"
                  />
                </div>
                <div>
                  <label className={labelClass}>Cost constraints{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.cost_constraints}
                    onChange={(e) => setProfile((p) => ({ ...p, cost_constraints: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Licensing considerations{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.licensing_considerations}
                    onChange={(e) => setProfile((p) => ({ ...p, licensing_considerations: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            )}

            {activePillar === 'security' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">6. Security</h2>
                <div>
                  <label className={labelClassFor('authentication_type')}>Authentication type{req}</label>
                  <input
                    type="text"
                    value={profile.authentication_type}
                    onChange={(e) => { clearInvalid('authentication_type'); setProfile((p) => ({ ...p, authentication_type: e.target.value })) }}
                    className={inputClassFor('authentication_type')}
                    placeholder="e.g. SAML, OAuth, AD, LDAP"
                  />
                  <RequiredMsg name="authentication_type" />
                </div>
                <div>
                  <label className={labelClassFor('encryption_at_rest')}>Encryption at rest{req}</label>
                  <input
                    type="text"
                    value={profile.encryption_at_rest}
                    onChange={(e) => { clearInvalid('encryption_at_rest'); setProfile((p) => ({ ...p, encryption_at_rest: e.target.value })) }}
                    className={inputClassFor('encryption_at_rest')}
                    placeholder="e.g. AES-256, TDE"
                  />
                  <RequiredMsg name="encryption_at_rest" />
                </div>
                <div>
                  <label className={labelClassFor('encryption_in_transit')}>Encryption in transit{req}</label>
                  <input
                    type="text"
                    value={profile.encryption_in_transit}
                    onChange={(e) => { clearInvalid('encryption_in_transit'); setProfile((p) => ({ ...p, encryption_in_transit: e.target.value })) }}
                    className={inputClassFor('encryption_in_transit')}
                    placeholder="e.g. TLS 1.2"
                  />
                  <RequiredMsg name="encryption_in_transit" />
                </div>
                <div>
                  <label className={labelClass}>PII handling{opt}</label>
                  <textarea
                    rows={2}
                    value={profile.pii_handling}
                    onChange={(e) => setProfile((p) => ({ ...p, pii_handling: e.target.value }))}
                    className={inputClass}
                    placeholder="How PII is stored, masked, etc."
                  />
                </div>
                <div>
                  <label className={labelClass}>Compliance frameworks (comma-separated){opt}</label>
                  <input
                    type="text"
                    value={listInputs.compliance_frameworks}
                    onChange={(e) => setListInputs((l) => ({ ...l, compliance_frameworks: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. SOC2, GDPR, HIPAA"
                  />
                </div>
              </div>
            )}

            {activePillar === 'project' && (
              <div className={sectionClass}>
                <h2 className="text-lg font-semibold text-slate-900">7. Project & Timeline</h2>
                <div>
                  <label className={labelClass}>Project manager / owner{opt}</label>
                  <input
                    type="text"
                    value={profile.project_manager}
                    onChange={(e) => setProfile((p) => ({ ...p, project_manager: e.target.value }))}
                    className={inputClass}
                    placeholder="Name or team"
                  />
                </div>
                <div>
                  <label className={labelClass}>Timeline expectation{opt}</label>
                  <input
                    type="text"
                    value={profile.timeline_expectation}
                    onChange={(e) => setProfile((p) => ({ ...p, timeline_expectation: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. 6 months"
                  />
                </div>
                <div>
                  <label className={labelClass}>Team size{opt}</label>
                  <input
                    type="text"
                    value={profile.team_size}
                    onChange={(e) => setProfile((p) => ({ ...p, team_size: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. 3-5"
                  />
                </div>
                <div>
                  <label className={labelClass}>Dependencies (comma-separated){opt}</label>
                  <input
                    type="text"
                    value={listInputs.dependencies}
                    onChange={(e) => setListInputs((l) => ({ ...l, dependencies: e.target.value }))}
                    className={inputClass}
                    placeholder="Other apps, databases"
                  />
                </div>
                <div>
                  <label className={labelClass}>Integrations{opt}</label>
                  <input
                    type="text"
                    value={listInputs.integrations}
                    onChange={(e) => setListInputs((l) => ({ ...l, integrations: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. SAP, Salesforce"
                  />
                </div>
                <div>
                  <label className={labelClass}>Preferred go-live window{opt}</label>
                  <input
                    type="text"
                    value={profile.preferred_go_live}
                    onChange={(e) => setProfile((p) => ({ ...p, preferred_go_live: e.target.value }))}
                    className={inputClass}
                    placeholder="e.g. Q2 2025"
                  />
                </div>
              </div>
            )}

            <div className="mt-8 flex justify-end gap-2">
              {getNextPillar(activePillar) ? (
                <button
                  type="button"
                  onClick={handleContinueToNextPillar}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700"
                >
                  Continue to {PILLARS[PILLAR_ORDER.indexOf(getNextPillar(activePillar))].label}
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {loading ? 'Saving…' : 'Submit for assessment'}
                </button>
              )}
            </div>
          </form>
        )}

        {step === 2 && status === 'submitted' && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-6">
            <h2 className="text-lg font-semibold text-emerald-900">Request submitted</h2>
            <p className="mt-2 text-slate-700">
              Your migration request has been submitted successfully.
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Admins will review your application details, run research, and produce an assessment report. You can check back later or you will be notified when the report is ready.
            </p>
          </div>
        )}

        {step === 2 && status !== 'submitted' && (
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Submit for assessment</h2>
            <p className="mt-1 text-slate-600">We’ll validate your input. Then submit your request; admins will run research and generate the report.</p>

            {(analysisPhase === 'analyzing' || analysisPhase === 'running') && analysisSteps.length > 0 && (
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-sm">
                <p className="mb-3 font-medium text-slate-700">Pre-submit check</p>
                <ul className="space-y-2">
                  {analysisSteps.map((s, i) => (
                    <li key={i} className="flex items-center gap-2">
                      {s.status === 'done' && <span className="text-emerald-600">✓</span>}
                      {s.status === 'active' && <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" />}
                      {s.status === 'pending' && <span className="text-slate-300">○</span>}
                      <span className={s.status === 'done' ? 'text-slate-600' : s.status === 'active' ? 'text-slate-900 font-medium' : 'text-slate-400'}>
                        {s.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysisPhase === 'review' && (
              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/50 p-4">
                <p className="font-medium text-amber-900">Please review the following</p>
                <p className="mt-1 text-sm text-amber-800">We found some values that may need confirmation. You can edit your profile or submit as is.</p>
                <div className="mt-3 space-y-2">
                  {analysisFindings.findings?.map((f, i) => (
                    <div key={`f-${i}`} className="rounded border border-amber-200 bg-white p-3 text-sm">
                      <span className={`font-medium ${f.severity === 'confirm' ? 'text-amber-700' : 'text-slate-700'}`}>
                        {f.field === 'rto' && 'RTO'}
                        {f.field === 'rpo' && 'RPO'}
                        {f.field === 'total_data_volume' && 'Data volume'}
                        {f.field === 'user_count_estimate' && 'User count'}
                        {!['rto', 'rpo', 'total_data_volume', 'user_count_estimate'].includes(f.field) && (f.field || '')}
                      </span>
                      <span className="text-slate-600"> ({f.value})</span>
                      <p className="mt-1 text-slate-700">{f.message}</p>
                    </div>
                  ))}
                  {analysisFindings.warnings?.map((w, i) => (
                    <p key={`w-${i}`} className="rounded border border-slate-200 bg-white p-2 text-sm text-slate-700">{w}</p>
                  ))}
                </div>
                <div className="mt-4 flex gap-3">
                  <button
                    type="button"
                    onClick={handleConfirmAndSubmit}
                    disabled={loading}
                    className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    I&apos;ve reviewed — Submit for assessment
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAnalysisPhase('idle'); setAnalysisSteps([]); setStep(1) }}
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Edit profile
                  </button>
                </div>
              </div>
            )}

            {validation && !validation.valid && validation.errors?.length > 0 && analysisPhase === 'idle' && (
              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                <p className="font-medium text-amber-800">Complete required fields</p>
                <p className="mt-1 text-sm text-amber-700">
                  Complete all required sections: Overview (RTO, RPO, users, priority), Architecture (description or diagram), Data (database migration answer; if Yes, data fields), BC &amp; DR, and Security (auth, encryption) before submitting.
                </p>
                <ul className="mt-2 list-inside list-disc text-sm text-amber-800">
                  {validation.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-50"
                >
                  Back to profile
                </button>
              </div>
            )}

            {validation?.warnings?.length > 0 && analysisPhase === 'idle' && (
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                {validation.warnings.map((w, i) => (
                  <p key={i}>{w}</p>
                ))}
              </div>
            )}

            {analysisPhase === 'idle' && (
              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={handleSubmitClick}
                  disabled={loading || validation === null || (validation && !validation.valid)}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Submit for assessment
                </button>
                {validation === null && (
                  <span className="text-sm text-slate-500">Checking profile…</span>
                )}
                {validation && !validation.valid && (
                  <span className="text-sm text-slate-500">Complete profile first</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
