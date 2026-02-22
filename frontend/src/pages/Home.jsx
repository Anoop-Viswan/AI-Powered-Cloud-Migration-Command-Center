import { useState } from 'react'
import { Link } from 'react-router-dom'

const PHASES = [
  { id: 'assessment', label: 'Assessment', icon: '📋' },
  { id: 'planning', label: 'Planning', icon: '📅' },
  { id: 'migration', label: 'Migration Implementation', icon: '🚀' },
  { id: 'support', label: 'Support', icon: '🛟' },
]

export default function Home() {
  const [activePhase, setActivePhase] = useState('assessment')

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200')] bg-cover bg-center opacity-30" />
        <div className="relative mx-auto max-w-6xl px-4 py-24 md:py-32">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
            Migration Center of Excellence
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-slate-300 md:text-xl">
            Your single place to assess, plan, and execute application migrations—with a shared knowledge base and best practices at every step.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              to="/chat"
              className="rounded-lg bg-emerald-500 px-6 py-3 font-semibold text-white shadow-lg transition hover:bg-emerald-600"
            >
              Ask the Knowledge Base
            </Link>
            <a
              href="#journey"
              className="rounded-lg border border-slate-500 bg-white/10 px-6 py-3 font-semibold backdrop-blur transition hover:bg-white/20"
            >
              Explore the journey
            </a>
          </div>
        </div>
      </section>

      {/* CoE – What we do */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-3xl font-bold text-slate-900">What we do</h2>
        <p className="mt-4 max-w-3xl text-lg text-slate-600">
          The Center of Excellence (CoE) supports architects and engineers through the full migration lifecycle. We provide assessment frameworks, planning tools, reusable artifacts, and a searchable knowledge base so every team can move faster with confidence.
        </p>
        <div className="mt-12 grid gap-8 md:grid-cols-3">
          {[
            { title: 'Assessment & Discovery', desc: 'Structured evaluation of applications, dependencies, and migration readiness.', img: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400' },
            { title: 'Planning & Roadmaps', desc: 'Timelines, dependencies, work breakdown, and project plans in one place.', img: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400' },
            { title: 'Knowledge Base', desc: 'Search and chat over migration docs, runbooks, and project artifacts.', img: 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=400' },
          ].map((card) => (
            <div key={card.title} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
              <img src={card.img} alt="" className="h-48 w-full object-cover" />
              <div className="p-5">
                <h3 className="font-semibold text-slate-900">{card.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{card.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Phase tabs – Migration journey */}
      <section id="journey" className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <h2 className="text-3xl font-bold text-slate-900">Migration journey</h2>
          <p className="mt-2 text-slate-600">Move through each phase with guided forms and artifacts.</p>

          <div className="mt-8 flex flex-wrap gap-2 border-b border-slate-200">
            {PHASES.map((p) => (
              <button
                key={p.id}
                onClick={() => setActivePhase(p.id)}
                className={`flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-3 font-medium transition ${
                  activePhase === p.id
                    ? 'border-emerald-500 bg-slate-50 text-emerald-700'
                    : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <span>{p.icon}</span>
                {p.label}
              </button>
            ))}
          </div>

          <div className="min-h-[320px] rounded-b-xl border border-t-0 border-slate-200 bg-slate-50/50 p-6 md:p-8">
            {activePhase === 'assessment' && (
              <AssessmentTab />
            )}
            {activePhase === 'planning' && (
              <PlanningTab />
            )}
            {activePhase === 'migration' && (
              <PlaceholderTab title="Migration Implementation" text="Guided implementation checklists and runbooks will go here." />
            )}
            {activePhase === 'support' && (
              <PlaceholderTab title="Support" text="Post-migration support and handover artifacts will go here." />
            )}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-slate-200 bg-slate-100 py-16">
        <div className="mx-auto max-w-6xl px-4 text-center">
          <p className="text-lg text-slate-700">Have a question about a migration or an existing project?</p>
          <Link to="/chat" className="mt-4 inline-block rounded-lg bg-slate-800 px-6 py-3 font-semibold text-white hover:bg-slate-900">
            Open the Knowledge Base chat
          </Link>
        </div>
      </section>
    </div>
  )
}

function PlaceholderTab({ title, text }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-xl font-semibold text-slate-700">{title}</p>
      <p className="mt-2 max-w-md text-slate-600">{text}</p>
      <p className="mt-4 text-sm text-slate-500">(Placeholder for future content)</p>
    </div>
  )
}

function AssessmentTab() {
  return (
    <div className="max-w-2xl">
      <h3 className="text-xl font-semibold text-slate-900">Application assessment</h3>
      <p className="mt-1 text-slate-600">Collect information about the application to be migrated. This starts your migration journey.</p>
      <form className="mt-6 space-y-4" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label className="block text-sm font-medium text-slate-700">Application name</label>
          <input type="text" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm" placeholder="e.g. Order Management Service" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Description</label>
          <textarea rows={3} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm" placeholder="Brief description of the application and its purpose" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Technology stack</label>
          <input type="text" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm" placeholder="e.g. Java 11, Spring Boot, Oracle DB" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Current environment</label>
          <select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm">
            <option value="">Select...</option>
            <option value="on-prem">On-premises</option>
            <option value="vm">Virtual machines</option>
            <option value="cloud-legacy">Cloud (legacy)</option>
          </select>
        </div>
        <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700">Save assessment</button>
      </form>
    </div>
  )
}

function PlanningTab() {
  return (
    <div className="max-w-2xl">
      <h3 className="text-xl font-semibold text-slate-900">Planning & project structure</h3>
      <p className="mt-1 text-slate-600">Project managers can capture timelines, dependencies, and build a work breakdown structure (WBS) or project plan.</p>
      <form className="mt-6 space-y-4" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label className="block text-sm font-medium text-slate-700">Target go-live date</label>
          <input type="date" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Key dependencies</label>
          <textarea rows={2} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm" placeholder="Other applications or teams this migration depends on" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Work breakdown (WBS) / Project plan</label>
          <textarea rows={4} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm font-mono text-sm" placeholder="Paste or describe phases, milestones, and tasks..." />
        </div>
        <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700">Save plan</button>
      </form>
    </div>
  )
}
