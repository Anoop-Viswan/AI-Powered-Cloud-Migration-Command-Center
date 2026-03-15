import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const API_BASE = import.meta.env?.VITE_API_BASE || ''

/**
 * Wraps admin routes: checks GET /api/admin/me. If 401, redirects to /admin/login.
 * If 200 (or admin auth not configured), renders children.
 */
export default function AdminGuard({ children }) {
  const [status, setStatus] = useState('loading') // 'loading' | 'ok' | 'unauthorized'
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/admin/me`, { credentials: 'include' })
      .then((r) => {
        if (cancelled) return
        if (r.status === 401) {
          setStatus('unauthorized')
          navigate('/admin/login', { state: { from: location }, replace: true })
        } else {
          setStatus('ok')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('ok') // on network error, allow through; API will 401 on first call
      })
    return () => { cancelled = true }
  }, [navigate, location])

  if (status === 'loading') {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-slate-500">Checking access…</p>
      </div>
    )
  }
  if (status === 'unauthorized') {
    return null
  }
  return children
}
