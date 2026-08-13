import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  throw new Error('VITE_API_BASE_URL is not set — check frontend/.env')
}

export const apiClient = axios.create({ baseURL })

const apiOrigin = new URL(baseURL).origin

/**
 * Report image_url values are root-relative (e.g. "/uploads/x.jpg"),
 * served by the backend. The frontend and backend are on different
 * origins in both dev (5173 vs 8000) and prod (separate Vercel/Render
 * hosts per PROJECT_SPEC), so a bare relative path would resolve
 * against the frontend's own origin and 404.
 */
export function resolveImageUrl(path: string): string {
  return `${apiOrigin}${path}`
}
