export type JobStatus =
  | 'DRAFT' | 'UPLOADED' | 'ARRANGING' | 'PROOFING'
  | 'APPROVED' | 'PRINTED' | 'SHIPPED'

export interface User {
  id: string
  email: string
  is_operator: boolean
}

export interface Job {
  id: string
  customer_id: string
  title: string
  wall_width_mm: number
  wall_height_mm: number
  status: JobStatus
  proof_url: string | null
  created_at: string
  updated_at: string
}

export interface Photo {
  id: string
  job_id: string
  filename: string
  storage_key: string
  width_px: number | null
  height_px: number | null
  size_bytes: number | null
  upload_confirmed: boolean
  url: string | null
  created_at: string
}

export interface Hole {
  id: string
  canvas_size_id: string
  label: string
  x_mm: number
  y_mm: number
}

export interface CanvasSize {
  id: string
  name: string
  width_mm: number
  height_mm: number
  thickness_mm: number
  price_cents: number
  active: boolean
  holes: Hole[]
  created_at: string
}

export interface Panel {
  id: string
  job_id: string
  canvas_size_id: string
  photo_id: string | null
  x_mm: number
  y_mm: number
  rotation_deg: number
  sort_order: number
  created_at: string
  updated_at: string
}

export interface EditorPanel {
  id: string
  canvas_size_id: string
  photo_id: string | null
  x_mm: number
  y_mm: number
  rotation_deg: number
  sort_order: number
}

export const STATUS_LABELS: Record<JobStatus, string> = {
  DRAFT: 'Draft',
  UPLOADED: 'Uploaded',
  ARRANGING: 'Arranging',
  PROOFING: 'Awaiting Approval',
  APPROVED: 'Approved',
  PRINTED: 'Printed',
  SHIPPED: 'Shipped',
}

export const STATUS_COLOURS: Record<JobStatus, string> = {
  DRAFT: 'bg-gray-100 text-gray-700',
  UPLOADED: 'bg-blue-100 text-blue-700',
  ARRANGING: 'bg-yellow-100 text-yellow-700',
  PROOFING: 'bg-purple-100 text-purple-700',
  APPROVED: 'bg-green-100 text-green-700',
  PRINTED: 'bg-teal-100 text-teal-700',
  SHIPPED: 'bg-emerald-100 text-emerald-700',
}
