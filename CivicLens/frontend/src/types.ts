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

export const STATUSES = ["reported", "acknowledged", "in_progress", "resolved", "rejected"] as const
export type Status = (typeof STATUSES)[number]

export const CATEGORIES = [
  "pothole",
  "garbage_dump",
  "broken_streetlight",
  "waterlogging",
  "damaged_road",
  "sewage_overflow",
  "broken_footpath",
  "fallen_tree",
  "stray_animals",
  "illegal_dumping",
  "other",
] as const
export type Category = (typeof CATEGORIES)[number]

export interface DashboardStats {
  total: number
  by_status: Record<string, number>
  by_category: Record<string, number>
  avg_resolution_hours: number | null
  high_priority_count: number
}
