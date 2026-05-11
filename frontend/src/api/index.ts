import api from './client'
import type { Job, Photo, Panel, CanvasSize, Hole, EditorPanel, User } from '../types'

// Auth
export const authApi = {
  register: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
}

// Jobs
export const jobsApi = {
  list: () => api.get<Job[]>('/jobs'),
  get: (id: string) => api.get<Job>(`/jobs/${id}`),
  create: (data: { title: string; wall_width_mm: number; wall_height_mm: number }) =>
    api.post<Job>('/jobs', data),
  update: (id: string, data: Partial<Pick<Job, 'title' | 'wall_width_mm' | 'wall_height_mm'>>) =>
    api.patch<Job>(`/jobs/${id}`, data),
  transition: (id: string, to: string) =>
    api.post<Job>(`/jobs/${id}/transition`, { to }),
  delete: (id: string) => api.delete(`/jobs/${id}`),
  sendProof: (id: string, proof_url: string) =>
    api.post<Job>(`/jobs/${id}/send-proof`, { proof_url }),
}

// Photos
export const photosApi = {
  presign: (jobId: string, filename: string, contentType: string, sizeBytes?: number) =>
    api.post<{
      photo_id: string; upload_url: string; method: string;
      headers: Record<string, string>; storage_key: string
    }>(`/jobs/${jobId}/photos/presign`, { filename, content_type: contentType, size_bytes: sizeBytes }),
  confirm: (jobId: string, photoId: string, data: { width_px?: number; height_px?: number; size_bytes?: number }) =>
    api.post<Photo>(`/jobs/${jobId}/photos/${photoId}/confirm`, data),
  list: (jobId: string) => api.get<Photo[]>(`/jobs/${jobId}/photos`),
  delete: (jobId: string, photoId: string) => api.delete(`/jobs/${jobId}/photos/${photoId}`),
}

// Panels
export const panelsApi = {
  list: (jobId: string) => api.get<Panel[]>(`/jobs/${jobId}/panels`),
  batchSave: (jobId: string, panels: EditorPanel[]) =>
    api.put<Panel[]>(`/jobs/${jobId}/panels`, { panels }),
  delete: (jobId: string, panelId: string) => api.delete(`/jobs/${jobId}/panels/${panelId}`),
}

// Catalog
export const catalogApi = {
  list: () => api.get<CanvasSize[]>('/catalog'),
  create: (data: Omit<CanvasSize, 'id' | 'holes' | 'created_at'>) =>
    api.post<CanvasSize>('/catalog', data),
  update: (id: string, data: Partial<CanvasSize>) =>
    api.patch<CanvasSize>(`/catalog/${id}`, data),
  addHole: (sizeId: string, hole: Omit<Hole, 'id' | 'canvas_size_id'>) =>
    api.post<Hole>(`/catalog/${sizeId}/holes`, hole),
  updateHole: (sizeId: string, holeId: string, hole: Omit<Hole, 'id' | 'canvas_size_id'>) =>
    api.patch<Hole>(`/catalog/${sizeId}/holes/${holeId}`, hole),
  deleteHole: (sizeId: string, holeId: string) =>
    api.delete(`/catalog/${sizeId}/holes/${holeId}`),
}

// PDFs
export const pdfApi = {
  templateUrl: (jobId: string) => `/api/jobs/${jobId}/pdf/template`,
  referenceUrl: (jobId: string) => `/api/jobs/${jobId}/pdf/reference`,
  printMastersUrl: (jobId: string) => `/api/jobs/${jobId}/export/print-masters`,
}
