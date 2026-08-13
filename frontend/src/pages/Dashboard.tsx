import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listReports, updateReportStatus } from '../api/reports'
import { getDashboardStats } from '../api/dashboard'
import { resolveImageUrl } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { CATEGORIES, STATUSES } from '../types'
import type { DashboardStats, ReportOut } from '../types'

const PRIORITY_BAND = (score: number): string => {
  if (score > 70) return 'bg-red-100 text-red-800'
  if (score >= 40) return 'bg-amber-100 text-amber-800'
  return 'bg-green-100 text-green-800'
}

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth()
  const [reports, setReports] = useState<ReportOut[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [minPriority, setMinPriority] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [reportsData, statsData] = await Promise.all([
        listReports({
          status: statusFilter || undefined,
          category: categoryFilter || undefined,
          min_priority: minPriority ? Number(minPriority) : undefined,
        }),
        getDashboardStats(),
      ])
      setReports(reportsData)
      setStats(statsData)
    } catch {
      setError('Failed to load dashboard data. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'authority') load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter, minPriority, user])

  async function handleStatusChange(reportId: number, newStatus: string) {
    setUpdatingId(reportId)
    try {
      const updated = await updateReportStatus(reportId, newStatus)
      setReports((prev) => prev.map((r) => (r.id === reportId ? updated : r)))
    } catch {
      setError(`Failed to update status for report #${reportId}.`)
    } finally {
      setUpdatingId(null)
    }
  }

  if (authLoading) return null

  if (!user || user.role !== 'authority') {
    return (
      <main className="mx-auto max-w-md px-6 py-10 text-center">
        <h1 className="text-2xl font-semibold">Authority dashboard</h1>
        <p className="mt-4 text-gray-500">
          {user
            ? "This page is restricted to authority accounts."
            : (
              <>
                <Link to="/login" className="underline">
                  Log in
                </Link>{' '}
                with an authority account to view the dashboard.
              </>
            )}
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-2xl font-semibold">Authority dashboard</h1>

      {stats && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total reports" value={stats.total} />
          <StatCard label="High priority" value={stats.high_priority_count} />
          <StatCard
            label="Avg. resolution"
            value={stats.avg_resolution_hours != null ? `${stats.avg_resolution_hours}h` : '—'}
          />
          <StatCard label="Resolved" value={stats.by_status.resolved ?? 0} />
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Min priority"
          value={minPriority}
          onChange={(e) => setMinPriority(e.target.value)}
          className="w-32 rounded-md border border-gray-300 px-2 py-1 text-sm"
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {loading && <p className="mt-4 text-sm text-gray-500">Loading…</p>}

      {!loading && !error && reports.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">No reports match these filters.</p>
      )}

      <div className="mt-4 space-y-3">
        {reports.map((report) => (
          <div key={report.id} className="flex gap-3 rounded-lg border border-gray-200 p-3">
            <img
              src={resolveImageUrl(report.image_url)}
              alt={report.category}
              className="h-20 w-20 rounded-md object-cover"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{report.category}</span>
                <span className={`rounded px-2 py-0.5 text-xs ${PRIORITY_BAND(report.priority_score)}`}>
                  {report.priority_score}
                </span>
                {report.report_count > 1 && (
                  <span className="text-xs text-gray-500">×{report.report_count} reports</span>
                )}
              </div>
              {report.description && <p className="text-sm text-gray-600">{report.description}</p>}
              <p className="text-xs text-gray-400">
                {report.address ?? `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}
              </p>
            </div>
            <select
              value={report.status}
              disabled={updatingId === report.id}
              onChange={(e) => handleStatusChange(report.id, e.target.value)}
              className="h-fit rounded-md border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </main>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3 text-center">
      <div className="text-xl font-semibold">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )
}
