import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { listReports } from '../api/reports'
import { resolveImageUrl } from '../api/client'
import type { ReportOut } from '../types'

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'

const GURUGRAM_CENTER: [number, number] = [28.4595, 77.0266]

function priorityColor(score: number): string {
  if (score > 70) return '#dc2626' // red
  if (score >= 40) return '#d97706' // amber
  return '#16a34a' // green
}

export default function MapView() {
  const [reports, setReports] = useState<ReportOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listReports({ limit: 200 })
      .then(setReports)
      .catch(() => setError('Failed to load reports. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-2xl font-semibold">Map</h1>

      {loading && <p className="mt-2 text-sm text-gray-500">Loading map…</p>}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      <div className="mt-4 h-[70vh] overflow-hidden rounded-lg border border-gray-200">
        <MapContainer center={GURUGRAM_CENTER} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url={TILE_URL}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {reports.map((report) => (
            <CircleMarker
              key={report.id}
              center={[report.latitude, report.longitude]}
              radius={9}
              pathOptions={{
                color: priorityColor(report.priority_score),
                fillColor: priorityColor(report.priority_score),
                fillOpacity: 0.8,
                weight: 2,
              }}
            >
              <Popup>
                <div className="w-40">
                  <img
                    src={resolveImageUrl(report.image_url)}
                    alt={report.category}
                    className="mb-2 h-24 w-full rounded object-cover"
                  />
                  <p className="font-medium capitalize">{report.category.replace('_', ' ')}</p>
                  <p className="text-sm">Priority: {report.priority_score}</p>
                  <p className="text-sm capitalize">Status: {report.status.replace('_', ' ')}</p>
                  {report.address && <p className="text-xs text-gray-500">{report.address}</p>}
                  {report.report_count > 1 && (
                    <p className="text-xs text-gray-500">{report.report_count} reports merged</p>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </main>
  )
}
