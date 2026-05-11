/**
 * Interactive hole-position editor for a canvas size.
 * The panel is drawn to scale. Click to add a hole. Drag to reposition.
 * All coordinates displayed and stored in mm from the panel top-left.
 */
import React, { useRef, useState, useCallback, useEffect } from 'react'
import { Stage, Layer, Rect, Line, Text, Circle, Group } from 'react-konva'
import type { KonvaEventObject } from 'konva/lib/Node'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { catalogApi } from '../../api'
import type { CanvasSize, Hole } from '../../types'
import toast from 'react-hot-toast'

interface Props {
  size: CanvasSize
  onBack: () => void
}

const EDITOR_MAX_W = 600
const EDITOR_MAX_H = 500
const RULER_SIZE = 30
const HOLE_RADIUS = 7

export function HoleEditor({ size, onBack }: Props) {
  const qc = useQueryClient()
  const containerRef = useRef<HTMLDivElement>(null)
  const [holes, setHoles] = useState<Hole[]>(size.holes)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editX, setEditX] = useState('')
  const [editY, setEditY] = useState('')

  const scale = Math.min(
    (EDITOR_MAX_W - RULER_SIZE) / size.width_mm,
    (EDITOR_MAX_H - RULER_SIZE) / size.height_mm,
  )
  const panelW = size.width_mm * scale
  const panelH = size.height_mm * scale
  const stageW = panelW + RULER_SIZE + 20
  const stageH = panelH + RULER_SIZE + 20

  const selected = holes.find(h => h.id === selectedId)

  useEffect(() => {
    if (selected) {
      setEditLabel(selected.label)
      setEditX(selected.x_mm.toFixed(1))
      setEditY(selected.y_mm.toFixed(1))
    }
  }, [selectedId])

  const addMutation = useMutation({
    mutationFn: (h: Omit<Hole, 'id' | 'canvas_size_id'>) => catalogApi.addHole(size.id, h),
    onSuccess: (r) => {
      setHoles(prev => [...prev, r.data])
      setSelectedId(r.data.id)
    },
    onError: (e: any) => toast.error('Failed to add hole'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Omit<Hole, 'id' | 'canvas_size_id'> }) =>
      catalogApi.updateHole(size.id, id, data),
    onSuccess: (r) => {
      setHoles(prev => prev.map(h => h.id === r.data.id ? r.data : h))
      toast.success('Hole saved')
    },
    onError: () => toast.error('Save failed'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => catalogApi.deleteHole(size.id, id),
    onSuccess: (_, id) => {
      setHoles(prev => prev.filter(h => h.id !== id))
      setSelectedId(null)
    },
  })

  const handlePanelClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage()!
    const pos = stage.getPointerPosition()!
    const x_mm = (pos.x - RULER_SIZE) / scale
    const y_mm = (pos.y - RULER_SIZE) / scale
    if (x_mm < 0 || y_mm < 0 || x_mm > size.width_mm || y_mm > size.height_mm) return
    addMutation.mutate({ label: `Hole ${holes.length + 1}`, x_mm: +x_mm.toFixed(1), y_mm: +y_mm.toFixed(1) })
  }, [scale, holes.length, addMutation, size])

  const handleHoleDrag = useCallback((id: string, e: KonvaEventObject<DragEvent>) => {
    const node = e.target
    const x_mm = +((node.x() - RULER_SIZE) / scale).toFixed(1)
    const y_mm = +((node.y() - RULER_SIZE) / scale).toFixed(1)
    setHoles(prev => prev.map(h => h.id === id ? { ...h, x_mm, y_mm } : h))
    if (selectedId === id) { setEditX(x_mm.toFixed(1)); setEditY(y_mm.toFixed(1)) }
  }, [scale, selectedId])

  const handleHoleDragEnd = useCallback((hole: Hole, e: KonvaEventObject<DragEvent>) => {
    const node = e.target
    const x_mm = +((node.x() - RULER_SIZE) / scale).toFixed(1)
    const y_mm = +((node.y() - RULER_SIZE) / scale).toFixed(1)
    updateMutation.mutate({ id: hole.id, data: { label: hole.label, x_mm, y_mm } })
  }, [scale, updateMutation])

  const handleSaveEdit = () => {
    if (!selected) return
    updateMutation.mutate({
      id: selected.id,
      data: { label: editLabel, x_mm: parseFloat(editX), y_mm: parseFloat(editY) },
    })
  }

  // Ruler tick marks
  const rulerTicksMm = []
  for (let x = 0; x <= size.width_mm; x += 50) rulerTicksMm.push(x)
  const rulerTicksY = []
  for (let y = 0; y <= size.height_mm; y += 50) rulerTicksY.push(y)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-wood-700 text-white px-6 py-4 flex items-center gap-4">
        <button onClick={onBack} className="text-wood-100 hover:text-white text-sm">← Back to catalog</button>
        <h1 className="text-xl font-bold">Hole Editor — {size.name}</h1>
        <span className="text-wood-200 text-sm">{size.width_mm} × {size.height_mm} mm</span>
      </header>

      <main className="px-6 py-6 flex gap-6">
        {/* Canvas */}
        <div ref={containerRef} className="card p-4">
          <p className="text-xs text-gray-500 mb-3">Click on the panel to add a hole. Drag to reposition.</p>
          <Stage width={stageW} height={stageH}>
            <Layer>
              {/* Rulers */}
              <Rect x={RULER_SIZE} y={RULER_SIZE} width={panelW} height={panelH} fill="white" stroke="#8B5E3C" strokeWidth={1.5} onClick={handlePanelClick} />

              {/* X ruler ticks */}
              {rulerTicksMm.map(v => (
                <React.Fragment key={`xr${v}`}>
                  <Line points={[RULER_SIZE + v * scale, RULER_SIZE - 5, RULER_SIZE + v * scale, RULER_SIZE]} stroke="#555" strokeWidth={1} />
                  <Text x={RULER_SIZE + v * scale - 10} y={2} text={String(v)} fontSize={8} fill="#555" />
                </React.Fragment>
              ))}

              {/* Y ruler ticks */}
              {rulerTicksY.map(v => (
                <React.Fragment key={`yr${v}`}>
                  <Line points={[RULER_SIZE - 5, RULER_SIZE + v * scale, RULER_SIZE, RULER_SIZE + v * scale]} stroke="#555" strokeWidth={1} />
                  <Text x={2} y={RULER_SIZE + v * scale - 4} text={String(v)} fontSize={8} fill="#555" />
                </React.Fragment>
              ))}

              {/* Holes — positioned in panel coordinates.
                  Group x/y = panel-local px + RULER_SIZE offset */}
              {holes.map(hole => {
                const hx = RULER_SIZE + hole.x_mm * scale
                const hy = RULER_SIZE + hole.y_mm * scale
                return (
                  <Group
                    key={hole.id}
                    x={hx}
                    y={hy}
                    draggable
                    dragBoundFunc={pos => ({
                      x: Math.max(RULER_SIZE, Math.min(RULER_SIZE + panelW, pos.x)),
                      y: Math.max(RULER_SIZE, Math.min(RULER_SIZE + panelH, pos.y)),
                    })}
                    onDragMove={e => handleHoleDrag(hole.id, e)}
                    onDragEnd={e => handleHoleDragEnd(hole, e)}
                    onClick={() => setSelectedId(hole.id)}
                  >
                    <Circle
                      radius={HOLE_RADIUS}
                      fill={selectedId === hole.id ? '#2563EB' : '#CC0000'}
                      opacity={0.85}
                    />
                    <Line
                      points={[-HOLE_RADIUS, -HOLE_RADIUS, HOLE_RADIUS, HOLE_RADIUS]}
                      stroke="white" strokeWidth={2} listening={false}
                    />
                    <Line
                      points={[HOLE_RADIUS, -HOLE_RADIUS, -HOLE_RADIUS, HOLE_RADIUS]}
                      stroke="white" strokeWidth={2} listening={false}
                    />
                    <Text
                      x={HOLE_RADIUS + 2} y={-5}
                      text={hole.label}
                      fontSize={9} fill="#333"
                      listening={false}
                    />
                  </Group>
                )
              })}
            </Layer>
          </Stage>
        </div>

        {/* Sidebar */}
        <div className="w-64 flex flex-col gap-4">
          <div className="card p-4">
            <p className="text-sm font-semibold mb-3">Holes ({holes.length})</p>
            {holes.length === 0 && (
              <p className="text-xs text-orange-500">⚠ No holes. A fallback centred hole will be used in the template.</p>
            )}
            <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
              {holes.map(h => (
                <button
                  key={h.id}
                  onClick={() => setSelectedId(h.id)}
                  className={`text-left px-2 py-1 rounded text-xs ${selectedId === h.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50'}`}
                >
                  {h.label} — ({h.x_mm}, {h.y_mm}) mm
                </button>
              ))}
            </div>
          </div>

          {selected && (
            <div className="card p-4">
              <p className="text-sm font-semibold mb-3">Edit hole</p>
              <div className="flex flex-col gap-2">
                <div>
                  <label className="label text-xs">Label</label>
                  <input className="input text-xs" value={editLabel} onChange={e => setEditLabel(e.target.value)} />
                </div>
                <div className="flex gap-2">
                  <div>
                    <label className="label text-xs">X (mm)</label>
                    <input className="input text-xs" type="number" step="0.1" value={editX} onChange={e => setEditX(e.target.value)} />
                  </div>
                  <div>
                    <label className="label text-xs">Y (mm)</label>
                    <input className="input text-xs" type="number" step="0.1" value={editY} onChange={e => setEditY(e.target.value)} />
                  </div>
                </div>
                <div className="flex gap-2 mt-1">
                  <button onClick={handleSaveEdit} disabled={updateMutation.isPending} className="btn-primary text-xs flex-1 justify-center">
                    Save
                  </button>
                  <button onClick={() => deleteMutation.mutate(selected.id)} className="btn-danger text-xs justify-center">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
