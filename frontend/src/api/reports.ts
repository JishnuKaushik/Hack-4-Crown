import { apiClient } from './client'
import type { ReportCreateResponse, ReportOut } from '../types'

export interface CreateReportInput {
  image: File
  latitude: number
  longitude: number
  description?: string
  address?: string
}

export async function createReport(input: CreateReportInput): Promise<ReportCreateResponse> {
  const form = new FormData()
  form.append('image', input.image)
  form.append('latitude', String(input.latitude))
  form.append('longitude', String(input.longitude))
  if (input.description) form.append('description', input.description)
  if (input.address) form.append('address', input.address)

  // Do not set Content-Type manually: the browser must generate the
  // multipart boundary itself when sending a FormData body.
  const { data } = await apiClient.post<ReportCreateResponse>('/reports', form)
  return data
}

export interface ListReportsFilters {
  status?: string
  category?: string
  min_priority?: number
  sort?: 'priority' | 'recent'
  limit?: number
}

export async function listReports(filters: ListReportsFilters = {}): Promise<ReportOut[]> {
  const { data } = await apiClient.get<ReportOut[]>('/reports', {
    params: { sort: 'priority', limit: 50, ...filters },
  })
  return data
}

export async function updateReportStatus(
  reportId: number,
  status: string,
  note?: string,
): Promise<ReportOut> {
  const { data } = await apiClient.patch<ReportOut>(`/reports/${reportId}/status`, { status, note })
  return data
}
