/**
 * WallEditor — Konva.js canvas-based wall layout editor.
 *
 * Coordinate contract:
 * - All data in store is mm (EditorPanel.x_mm, y_mm, etc.)
 * - Canvas renders at `scale` px/mm, computed to fit the viewport
 * - On drag end: pixel coords divided by scale → mm, snapped to 10mm grid
 * - Rotation stored as degrees, applied via Konva's rotation prop
 */
import React, { useRef, useCallback, useEffect, useState } from 'react'
import { Stage, Layer, Rect, Group, Text, Line, Circle, Image as KonvaImage } from 'react-konva'
import useImage from 'use-image'
import type { KonvaEventObject } from 'konva/lib/Node'
import { useEditorStore } from '../../stores/editorStore'
import type { CanvasSize, Photo, EditorPanel } from '../../types'
import { v4 as uuidv4 } from 'uuid'

const GRID_COLOUR = '#e5e7eb'
const PANEL_FILL = 'rgba(139,94,60,0.08)'
const PANEL_STROKE = '#8B5E3C'
const PANEL_SELECTED = '#2563EB'
const HOLE_COLOUR = '#CC0000'
const SNAP_MM = 10

interface Props {
  wallWidthMm: number
  wallHeightMm: number
  readOnly?: boolean
  onchange?: () => void
}

// Scale mm to px given a target canvas size
function computeScale(wallW: number, wallH: number, maxW: number, maxH: number): number {
  return Math.min(maxW / wallW, maxH / wallH)
}

function PanelImage({ src, x, y, width, height }: { src: string; x: number; y: number; width: number; height: number }) {
  const [img, status] = useImage(src)
  if (!img || status !== 'loaded') return null
  return <KonvaImage image={img} x={x} y={y} width={width} height={height} listening={false} />
}

interface PanelShapeProps {
  panel: EditorPanel
  scale: number
  canvasSize: CanvasSize | undefined
  photo: Photo | undefined
  holes: { x_mm: number; y_mm: number; label: string }[]
  selected: boolean
  readOnly: boolean
  wallWidthPx: number
  wallHeightPx: number
  onSelect: () => void
  onDragEnd: (x_mm: number, y_mm: number) => void
  onDragStart: () => void
}

function PanelShape({ panel, scale, canvasSize, photo, holes, selected, readOnly,
  wallWidthPx, wallHeightPx,
  onSelect, onDragEnd, onDragStart }: PanelShapeProps) {
  if (!canvasSize) return null

  const w = canvasSize.width_mm * scale
  const h = canvasSize.height_mm * scale
  const x = panel.x_mm * scale
  const y = panel.y_mm * scale

  const handleDragEnd = useCallback((e: KonvaEventObject<DragEvent>) => {
    const node = e.target
    // node.x()/y() are layer-relative (layer has its own offset already applied)
    const newX = node.x() / scale
    const newY = node.y() / scale
    onDragEnd(newX, newY)
  }, [scale, onDragEnd])

  return (
    <Group
      x={x} y={y}
      rotation={panel.rotation_deg}
      offset={{ x: w / 2, y: h / 2 }}
      draggable={!readOnly}
      onDragMove={e => {
        // node.x/y() are layer-relative. With offset {w/2, h/2} and rect at (-w/2,-h/2),
        // the rect's top-left = (node.x-w, node.y-h) and bottom-right = (node.x, node.y).
        // Clamp so all four sides stay within the wall (0..wallWidthPx, 0..wallHeightPx).
        const node = e.target
        node.x(Math.max(w, Math.min(wallWidthPx, node.x())))
        node.y(Math.max(h, Math.min(wallHeightPx, node.y())))
      }}
      onClick={onSelect}
      onTap={onSelect}
      onDragStart={onDragStart}
      onDragEnd={handleDragEnd}
    >
      {/* Panel background */}
      <Rect
        x={-w / 2} y={-h / 2}
        width={w} height={h}
        fill={selected ? 'rgba(37,99,235,0.08)' : PANEL_FILL}
        stroke={selected ? PANEL_SELECTED : PANEL_STROKE}
        strokeWidth={selected ? 2 : 1}
        cornerRadius={2}
      />

      {/* Photo thumbnail */}
      {photo?.url && (
        <PanelImage
          src={photo.url}
          x={-w / 2} y={-h / 2}
          width={w} height={h}
        />
      )}

      {/* Panel label */}
      <Text
        x={-w / 2} y={-h / 2 + 4}
        width={w}
        text={canvasSize.name}
        fontSize={Math.max(8, Math.min(12, w / 8))}
        fill={selected ? PANEL_SELECTED : '#4B3A2A'}
        align="center"
        listening={false}
      />

      {/* Hole marks */}
      {holes.map((hole, i) => {
        const hx = (hole.x_mm - canvasSize.width_mm / 2) * scale
        const hy = (hole.y_mm - canvasSize.height_mm / 2) * scale
        const r = Math.max(3, scale * 2)
        return (
          <React.Fragment key={i}>
            <Line points={[hx - r, hy - r, hx + r, hy + r]} stroke={HOLE_COLOUR} strokeWidth={1.5} listening={false} />
            <Line points={[hx + r, hy - r, hx - r, hy + r]} stroke={HOLE_COLOUR} strokeWidth={1.5} listening={false} />
          </React.Fragment>
        )
      })}
    </Group>
  )
}

export function WallEditor({ wallWidthMm, wallHeightMm, readOnly = false, onchange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [canvasSize, setCanvasSize] = useState({ w: 800, h: 600 })

  const { panels, canvasSizes, photos, selectedId, select, movePanel, addPanel, snap } = useEditorStore()

  useEffect(() => {
    if (!containerRef.current) return
    const obs = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      setCanvasSize({ w: Math.floor(width), h: Math.floor(height - 4) })
    })
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  const scale = computeScale(wallWidthMm, wallHeightMm, canvasSize.w - 2, canvasSize.h - 2)
  const drawnW = wallWidthMm * scale
  const drawnH = wallHeightMm * scale
  const offsetX = (canvasSize.w - drawnW) / 2
  const offsetY = (canvasSize.h - drawnH) / 2

  // Grid lines
  const gridLines: React.ReactNode[] = []
  for (let x = 0; x <= wallWidthMm; x += SNAP_MM) {
    gridLines.push(
      <Line key={`vg${x}`} points={[x * scale, 0, x * scale, drawnH]}
        stroke={GRID_COLOUR} strokeWidth={0.5} listening={false} />
    )
  }
  for (let y = 0; y <= wallHeightMm; y += SNAP_MM) {
    gridLines.push(
      <Line key={`hg${y}`} points={[0, y * scale, drawnW, y * scale]}
        stroke={GRID_COLOUR} strokeWidth={0.5} listening={false} />
    )
  }

  const handleStageClick = useCallback((e: KonvaEventObject<MouseEvent>) => {
    if (e.target === e.target.getStage()) select(null)
  }, [select])

  const handleDropOnWall = useCallback((e: React.DragEvent) => {
    if (readOnly) return
    e.preventDefault()
    const photoId = e.dataTransfer.getData('photo_id')
    const canvasSizeId = e.dataTransfer.getData('canvas_size_id') || canvasSizes[0]?.id
    if (!canvasSizeId) return

    const rect = containerRef.current!.getBoundingClientRect()
    const px = e.clientX - rect.left - offsetX
    const py = e.clientY - rect.top - offsetY
    const x_mm = snap(px / scale)
    const y_mm = snap(py / scale)

    const newPanel: EditorPanel = {
      id: uuidv4(),
      canvas_size_id: canvasSizeId,
      photo_id: photoId || null,
      x_mm, y_mm,
      rotation_deg: 0,
      sort_order: panels.length,
    }
    addPanel(newPanel)
    onchange?.()
  }, [readOnly, canvasSizes, scale, offsetX, offsetY, panels.length, addPanel, snap, onchange])

  return (
    <div
      ref={containerRef}
      className="relative flex-1 bg-gray-100 rounded-lg overflow-hidden"
      style={{ minHeight: 400 }}
      onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy' }}
      onDrop={handleDropOnWall}
    >
      <Stage
        width={canvasSize.w}
        height={canvasSize.h}
        onClick={handleStageClick}
      >
        <Layer x={offsetX} y={offsetY}>
          {/* Wall background */}
          <Rect x={0} y={0} width={drawnW} height={drawnH} fill="white" stroke="#CBD5E1" strokeWidth={1} />

          {/* Grid */}
          {gridLines}

          {/* Panels */}
          {panels.map(panel => {
            const cs = canvasSizes.find(s => s.id === panel.canvas_size_id)
            const photo = photos.find(p => p.id === panel.photo_id)
            const holes = cs?.holes?.length
              ? cs.holes
              : cs ? [{ x_mm: cs.width_mm / 2, y_mm: 50, label: 'fallback' }] : []

            return (
              <PanelShape
                key={panel.id}
                panel={panel}
                scale={scale}
                canvasSize={cs}
                photo={photo}
                holes={holes}
                selected={selectedId === panel.id}
                readOnly={readOnly}
                wallWidthPx={drawnW}
                wallHeightPx={drawnH}
                onSelect={() => select(panel.id)}
                onDragStart={() => select(panel.id)}
                onDragEnd={(x, y) => {
                  movePanel(panel.id, x, y)
                  onchange?.()
                }}
              />
            )
          })}
        </Layer>
      </Stage>

      {/* Dimensions label */}
      <div className="absolute bottom-2 right-2 text-xs text-gray-400 bg-white/80 px-2 py-0.5 rounded">
        {wallWidthMm} × {wallHeightMm} mm
      </div>
    </div>
  )
}
