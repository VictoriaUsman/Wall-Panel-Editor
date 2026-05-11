/**
 * Wall editor state with 20-step undo/redo history.
 * All coordinates are in millimetres. No pixels in this store.
 */
import { create } from 'zustand'
import type { EditorPanel, CanvasSize, Photo } from '../types'

const SNAP_MM = 10
const MAX_HISTORY = 20

interface EditorState {
  panels: EditorPanel[]
  history: EditorPanel[][]
  historyIndex: number

  // Catalog + photos available in this job
  canvasSizes: CanvasSize[]
  photos: Photo[]

  // Currently selected panel id
  selectedId: string | null

  // Actions
  setInitial: (panels: EditorPanel[], sizes: CanvasSize[], photos: Photo[]) => void
  addPhoto: (photo: Photo) => void
  removePhoto: (photoId: string) => void

  addPanel: (panel: EditorPanel) => void
  updatePanel: (id: string, updates: Partial<EditorPanel>) => void
  removePanel: (id: string) => void
  movePanel: (id: string, x_mm: number, y_mm: number) => void
  rotatePanel: (id: string, rotation_deg: number) => void
  resizePanel: (id: string, canvas_size_id: string) => void
  swapPhoto: (panelId: string, photoId: string) => void
  select: (id: string | null) => void

  undo: () => void
  redo: () => void
  canUndo: () => boolean
  canRedo: () => boolean

  // Snap a mm value to the 10mm grid
  snap: (v: number) => number
}

function snapToGrid(v: number): number {
  return Math.round(v / SNAP_MM) * SNAP_MM
}

export const useEditorStore = create<EditorState>()((set, get) => ({
  panels: [],
  history: [],
  historyIndex: -1,
  canvasSizes: [],
  photos: [],
  selectedId: null,

  snap: snapToGrid,

  setInitial(panels, sizes, photos) {
    set({ panels, canvasSizes: sizes, photos, history: [panels], historyIndex: 0, selectedId: null })
  },

  addPhoto(photo) {
    set(s => ({ photos: [...s.photos, photo] }))
  },

  removePhoto(photoId) {
    set(s => ({
      photos: s.photos.filter(p => p.id !== photoId),
      panels: s.panels.map(p => p.photo_id === photoId ? { ...p, photo_id: null } : p),
    }))
  },

  _pushHistory(newPanels: EditorPanel[]) {
    set(s => {
      const newHistory = s.history.slice(0, s.historyIndex + 1).concat([newPanels])
      const trimmed = newHistory.length > MAX_HISTORY ? newHistory.slice(newHistory.length - MAX_HISTORY) : newHistory
      return { history: trimmed, historyIndex: trimmed.length - 1, panels: newPanels }
    })
  },

  addPanel(panel) {
    const newPanels = [...get().panels, panel]
    ;(get() as any)._pushHistory(newPanels)
  },

  updatePanel(id, updates) {
    const newPanels = get().panels.map(p => p.id === id ? { ...p, ...updates } : p)
    ;(get() as any)._pushHistory(newPanels)
  },

  removePanel(id) {
    const newPanels = get().panels.filter(p => p.id !== id)
    ;(get() as any)._pushHistory(newPanels)
    if (get().selectedId === id) set({ selectedId: null })
  },

  movePanel(id, x_mm, y_mm) {
    const snapped_x = snapToGrid(x_mm)
    const snapped_y = snapToGrid(y_mm)
    const newPanels = get().panels.map(p => p.id === id ? { ...p, x_mm: snapped_x, y_mm: snapped_y } : p)
    ;(get() as any)._pushHistory(newPanels)
  },

  rotatePanel(id, rotation_deg) {
    const newPanels = get().panels.map(p => p.id === id ? { ...p, rotation_deg } : p)
    ;(get() as any)._pushHistory(newPanels)
  },

  resizePanel(id, canvas_size_id) {
    const newPanels = get().panels.map(p => p.id === id ? { ...p, canvas_size_id } : p)
    ;(get() as any)._pushHistory(newPanels)
  },

  swapPhoto(panelId, photoId) {
    const newPanels = get().panels.map(p => p.id === panelId ? { ...p, photo_id: photoId } : p)
    ;(get() as any)._pushHistory(newPanels)
  },

  select(id) {
    set({ selectedId: id })
  },

  undo() {
    const { historyIndex, history } = get()
    if (historyIndex <= 0) return
    const newIndex = historyIndex - 1
    set({ historyIndex: newIndex, panels: history[newIndex] })
  },

  redo() {
    const { historyIndex, history } = get()
    if (historyIndex >= history.length - 1) return
    const newIndex = historyIndex + 1
    set({ historyIndex: newIndex, panels: history[newIndex] })
  },

  canUndo: () => get().historyIndex > 0,
  canRedo: () => get().historyIndex < get().history.length - 1,
}))
