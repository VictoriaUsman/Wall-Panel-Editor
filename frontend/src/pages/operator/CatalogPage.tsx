import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { catalogApi } from '../../api'
import type { CanvasSize, Hole } from '../../types'
import toast from 'react-hot-toast'
import { HoleEditor } from './HoleEditor'

export function CatalogPage() {
  const qc = useQueryClient()
  const [editingSize, setEditingSize] = useState<CanvasSize | null>(null)
  const [holeEditingSize, setHoleEditingSize] = useState<CanvasSize | null>(null)
  const [newSize, setNewSize] = useState({ name: '', width_mm: 300, height_mm: 400, thickness_mm: 18, price_cents: 0, active: true })
  const [showNew, setShowNew] = useState(false)

  const { data: sizes, isLoading } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => catalogApi.list().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => catalogApi.create(newSize),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['catalog'] }); setShowNew(false); toast.success('Size created') },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CanvasSize> }) => catalogApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['catalog'] }); setEditingSize(null); toast.success('Updated') },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  if (holeEditingSize) {
    return (
      <HoleEditor
        size={holeEditingSize}
        onBack={() => { setHoleEditingSize(null); qc.invalidateQueries({ queryKey: ['catalog'] }) }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-wood-700 text-white px-6 py-4 flex items-center gap-4">
        <Link to="/operator" className="text-wood-100 hover:text-white text-sm">← Pipeline</Link>
        <h1 className="text-xl font-bold">Canvas Size Catalog</h1>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-semibold">All sizes</h2>
          <button onClick={() => setShowNew(true)} className="btn-primary">+ Add size</button>
        </div>

        {showNew && (
          <div className="card p-5 mb-6">
            <h3 className="font-semibold mb-4">New canvas size</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="col-span-2">
                <label className="label">Name</label>
                <input className="input" value={newSize.name} onChange={e => setNewSize(s => ({ ...s, name: e.target.value }))} placeholder="30×40 Portrait" />
              </div>
              <div>
                <label className="label">Width (mm)</label>
                <input className="input" type="number" value={newSize.width_mm} onChange={e => setNewSize(s => ({ ...s, width_mm: +e.target.value }))} />
              </div>
              <div>
                <label className="label">Height (mm)</label>
                <input className="input" type="number" value={newSize.height_mm} onChange={e => setNewSize(s => ({ ...s, height_mm: +e.target.value }))} />
              </div>
              <div>
                <label className="label">Thickness (mm)</label>
                <input className="input" type="number" value={newSize.thickness_mm} onChange={e => setNewSize(s => ({ ...s, thickness_mm: +e.target.value }))} />
              </div>
              <div>
                <label className="label">Price (pence/cents)</label>
                <input className="input" type="number" value={newSize.price_cents} onChange={e => setNewSize(s => ({ ...s, price_cents: +e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => createMutation.mutate()} disabled={!newSize.name || createMutation.isPending} className="btn-primary">
                {createMutation.isPending ? 'Creating…' : 'Create'}
              </button>
              <button onClick={() => setShowNew(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        )}

        {isLoading ? <div className="text-gray-400">Loading…</div> : (
          <div className="flex flex-col gap-3">
            {sizes?.map(size => (
              <div key={size.id} className={`card p-4 flex items-center gap-4 ${!size.active ? 'opacity-50' : ''}`}>
                <div className="flex-1">
                  <p className="font-medium">{size.name}</p>
                  <p className="text-sm text-gray-500">
                    {size.width_mm} × {size.height_mm} mm · {size.thickness_mm}mm thick · £{(size.price_cents / 100).toFixed(2)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {size.holes.length === 0
                      ? <span className="text-orange-500">⚠ No hole config (fallback: centre, 50mm from top)</span>
                      : `${size.holes.length} hole${size.holes.length !== 1 ? 's' : ''} configured`}
                  </p>
                </div>
                <button onClick={() => setHoleEditingSize(size)} className="btn-secondary text-xs">Edit holes</button>
                <button
                  onClick={() => updateMutation.mutate({ id: size.id, data: { active: !size.active } })}
                  className={`btn-secondary text-xs ${!size.active ? 'text-green-600' : 'text-gray-600'}`}
                >
                  {size.active ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
