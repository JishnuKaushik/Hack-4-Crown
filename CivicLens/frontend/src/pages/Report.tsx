import { useState } from 'react'
import { createReport } from '../api/reports'
import { resolveImageUrl } from '../api/client'
import type { ReportCreateResponse } from '../types'

type Coords = { latitude: number; longitude: number }

export default function Report() {
  const [image, setImage] = useState<File | null>(null)
  const [coords, setCoords] = useState<Coords | null>(null)
  const [manualLat, setManualLat] = useState('')
  const [manualLng, setManualLng] = useState('')
  const [description, setDescription] = useState('')
  const [address, setAddress] = useState('')
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<ReportCreateResponse | null>(null)

  function useMyLocation() {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported on this device — enter coordinates manually.')
      return
    }
    setLocating(true)
    setLocationError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ latitude: pos.coords.latitude, longitude: pos.coords.longitude })
        setLocating(false)
      },
      (err) => {
        setLocationError(`Could not get location (${err.message}) — enter coordinates manually.`)
        setLocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  const effectiveCoords: Coords | null =
    coords ??
    (manualLat && manualLng && !Number.isNaN(Number(manualLat)) && !Number.isNaN(Number(manualLng))
      ? { latitude: Number(manualLat), longitude: Number(manualLng) }
      : null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitError(null)

    if (!image) {
      setSubmitError('Please attach a photo of the issue.')
      return
    }
    if (!effectiveCoords) {
      setSubmitError('Please share your location or enter coordinates manually.')
      return
    }

    setSubmitting(true)
    try {
      const res = await createReport({
        image,
        latitude: effectiveCoords.latitude,
        longitude: effectiveCoords.longitude,
        description: description || undefined,
        address: address || undefined,
      })
      setResult(res)
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Failed to submit report. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <main className="mx-auto max-w-md px-6 py-10">
        <h1 className="text-2xl font-semibold">Report submitted</h1>
        <div className="mt-4 space-y-2 rounded-lg border border-gray-200 p-4">
          <img
            src={resolveImageUrl(result.report.image_url)}
            alt="Submitted issue"
            className="w-full rounded-md object-cover"
          />
          <p>
            <span className="font-medium">Category:</span> {result.report.category}
          </p>
          <p>
            <span className="font-medium">Severity:</span> {result.report.severity}/5
          </p>
          <p>
            <span className="font-medium">Priority score:</span> {result.report.priority_score}
          </p>
          {result.duplicate_of && (
            <p className="text-amber-600">Merged with existing report #{result.duplicate_of}</p>
          )}
        </div>
        <button
          type="button"
          className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-white"
          onClick={() => {
            setResult(null)
            setImage(null)
            setDescription('')
            setAddress('')
          }}
        >
          Report another issue
        </button>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-md px-6 py-10">
      <h1 className="text-2xl font-semibold">Report an issue</h1>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-sm font-medium" htmlFor="photo">
            Photo
          </label>
          <input
            id="photo"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full"
          />
        </div>

        <div>
          <button
            type="button"
            onClick={useMyLocation}
            disabled={locating}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
          >
            {locating ? 'Locating…' : 'Use my location'}
          </button>
          {coords && (
            <p className="mt-1 text-sm text-gray-500">
              {coords.latitude.toFixed(5)}, {coords.longitude.toFixed(5)}
            </p>
          )}
          {locationError && <p className="mt-1 text-sm text-red-600">{locationError}</p>}

          {!coords && (
            <div className="mt-2 grid grid-cols-2 gap-2">
              <input
                type="number"
                step="any"
                placeholder="Latitude"
                value={manualLat}
                onChange={(e) => setManualLat(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm"
              />
              <input
                type="number"
                step="any"
                placeholder="Longitude"
                value={manualLng}
                onChange={(e) => setManualLng(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium" htmlFor="address">
            Address (optional)
          </label>
          <input
            id="address"
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium" htmlFor="description">
            Description (optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            rows={3}
          />
        </div>

        {submitError && <p className="text-sm text-red-600">{submitError}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {submitting ? 'Submitting…' : 'Submit report'}
        </button>
      </form>
    </main>
  )
}
