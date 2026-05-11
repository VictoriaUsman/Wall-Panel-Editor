import React from 'react'
import { useEditorStore } from '../../stores/editorStore'

interface Props {
  readOnly?: boolean
  onchange?: () => void
}

export function PanelControls({ readOnly = false, onchange }: Props) {
  const {
    selectedId, panels, canvasSizes, photos,
    removePanel, rotatePanel, resizePanel, swapPhoto,
    undo, redo, canUndo, canRedo,
  } = useEditorStore()

  const selected = panels.find(p => p.id === selectedId)
  const selectedCs = selected ? canvasSizes.find(cs => cs.id === selected.canvas_size_id) : null

  const handleRotate = (deg: number) => {
    if (!selectedId) return
    const cur = selected?.rotation_deg ?? 0
    rotatePanel(selectedId, (cur + deg + 360) % 360)
    onchange?.()
  }

  const handleRemove = () => {
    if (!selectedId) return
    removePanel(selectedId)
    onchange?.()
  }

  const handleResize = (sizeId: string) => {
    if (!selectedId) return
    resizePanel(selectedId, sizeId)
    onchange?.()
  }

  const handleSwapPhoto = (photoId: string) => {
    if (!selectedId) return
    swapPhoto(selectedId, photoId)
    onchange?.()
  }

  return (
    <div className="w-44 shrink-0 flex flex-col gap-3">
      {/* Undo/Redo */}
      <div className="flex gap-2">
        <button
          onClick={() => { undo(); onchange?.() }}
          disabled={!canUndo()}
          className="btn-secondary flex-1 justify-center disabled:opacity-40"
          title="Undo (Ctrl+Z)"
        >↩</button>
        <button
          onClick={() => { redo(); onchange?.() }}
          disabled={!canRedo()}
          className="btn-secondary flex-1 justify-center disabled:opacity-40"
          title="Redo (Ctrl+Shift+Z)"
        >↪</button>
      </div>

      {selected && !readOnly ? (
        <div className="card p-3 flex flex-col gap-3">
          <p className="text-xs font-semibold text-gray-700">Selected panel</p>

          {/* Size */}
          <div>
            <label className="label">Size</label>
            <select
              className="input text-xs"
              value={selected.canvas_size_id}
              onChange={e => handleResize(e.target.value)}
            >
              {canvasSizes.filter(cs => cs.active).map(cs => (
                <option key={cs.id} value={cs.id}>{cs.name} ({cs.width_mm}×{cs.height_mm}mm)</option>
              ))}
            </select>
          </div>

          {/* Photo */}
          <div>
            <label className="label">Photo</label>
            <select
              className="input text-xs"
              value={selected.photo_id ?? ''}
              onChange={e => handleSwapPhoto(e.target.value)}
            >
              <option value="">— none —</option>
              {photos.filter(p => p.upload_confirmed).map(p => (
                <option key={p.id} value={p.id}>{p.filename}</option>
              ))}
            </select>
          </div>

          {/* Rotation */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Rotation</label>
              <span className="text-xs text-gray-500 font-mono">{selected.rotation_deg}°</span>
            </div>
            <div className="flex gap-1">
              {[90, -90, 180].map(deg => (
                <button key={deg} onClick={() => handleRotate(deg)} className="btn-secondary flex-1 text-xs px-1">
                  {deg > 0 ? `+${deg}°` : `${deg}°`}
                </button>
              ))}
            </div>
          </div>

          {/* Position */}
          <div className="text-xs text-gray-500">
            <p>X: {selected.x_mm} mm</p>
            <p>Y: {selected.y_mm} mm</p>
            {selectedCs && <p className="mt-1 text-gray-400">{selectedCs.width_mm} × {selectedCs.height_mm} mm</p>}
          </div>

          {/* Remove */}
          <button onClick={handleRemove} className="btn-danger text-xs justify-center">
            Remove panel
          </button>
        </div>
      ) : (
        <div className="card p-3 text-xs text-gray-400 text-center">
          {readOnly ? 'Read-only view' : 'Select a panel to edit it'}
        </div>
      )}

      <div className="card p-3">
        <p className="text-xs text-gray-500">{panels.length} panel{panels.length !== 1 ? 's' : ''}</p>
        <p className="text-xs text-gray-400 mt-1">Drag photos from tray to add</p>
        <p className="text-xs text-gray-400">Snaps to 10mm grid</p>
      </div>
    </div>
  )
}
