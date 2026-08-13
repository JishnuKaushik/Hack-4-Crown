import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, resolveImageUrl } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { ReportOut } from '../types'

export default function Track() {
  const { user, loading: authLoading } = useAuth()
  const [reports, setReports] = useState<ReportOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading || !user) {
      setLoading(false)
      return
    }
    apiClient
      .get<ReportOut[]>('/reports/mine')
      .then((res) => setReports(res.data))
      .catch(() => setError('Failed to load your reports.'))
      .finally(() => setLoading(false))
  }, [authLoading, user])

  if (authLoading) return null

  if (!user) {
    return (
      <main className="mx-auto max-w-md px-6 py-10 text-center">
        <h1 className="text-2xl font-semibold">My reports</h1>
        <p className="mt-4 text-gray-500">
          <Link to="/login" className="underline">
            Log in
          </Link>{' '}
          to see the reports you've submitted.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="text-2xl font-semibold">My reports</h1>

      {loading && <p className="mt-4 text-sm text-gray-500">Loading…</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {!loading && !error && reports.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">
          You haven't reported any issues yet.{' '}
          <Link to="/" className="underline">
            Report one
          </Link>
          .
        </p>
      )}

      <div className="mt-4 space-y-3">
        {reports.map((report) => (
          <div key={report.id} className="flex gap-3 rounded-lg border border-gray-200 p-3">
            <img
              src={resolveImageUrl(report.image_url)}
              alt={report.category}
              className="h-16 w-16 rounded-md object-cover"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{report.category}</span>
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs capitalize text-gray-700">
                  {report.status.replace('_', ' ')}
                </span>
              </div>
              {report.description && <p className="text-sm text-gray-600">{report.description}</p>}
              <p className="text-xs text-gray-400">{new Date(report.created_at).toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}
