import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Chat from './pages/Chat'
import Admin from './pages/Admin'
import AdminAssessmentDetail from './pages/AdminAssessmentDetail'
import AdminLogin from './pages/AdminLogin'
import Assessment from './pages/Assessment'
import AdminGuard from './AdminGuard'

function NavLink({ to, children }) {
  const loc = useLocation()
  const active = loc.pathname === to
  return (
    <Link
      to={to}
      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
        active ? 'bg-slate-800 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }`}
    >
      {children}
    </Link>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="text-xl font-semibold text-slate-900">
            Center of Excellence
          </Link>
          <nav className="flex items-center gap-2">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/assessment">Assessment</NavLink>
            <NavLink to="/chat">Ask the KB</NavLink>
            <NavLink to="/admin">Admin</NavLink>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/assessment" element={<Assessment />} />
          <Route path="/assessment/:id" element={<Assessment />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminGuard><Admin /></AdminGuard>} />
          <Route path="/admin/assessment/:id" element={<AdminGuard><AdminAssessmentDetail /></AdminGuard>} />
        </Routes>
      </main>
    </div>
  )
}
