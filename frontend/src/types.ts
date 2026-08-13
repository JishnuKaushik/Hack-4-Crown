export interface ReportOut {
  id: number
  image_url: string
  latitude: number
  longitude: number
  address: string | null
  description: string | null
  category: string
  ai_confidence: number
  severity: number
  status: string
  priority_score: number
  report_count: number
  is_duplicate_of: number | null
  created_at: string
  updated_at: string
}

export interface ReportCreateResponse {
  report: ReportOut
  duplicate_of: number | null
}
