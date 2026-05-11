import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, authApi } from '../../api'
import { useAuthStore } from '../../stores/authStore'
import { STATUS_LABELS, STATUS_COLOURS } from '../../types'
import type { Job } from '../../types'
import toast from 'react-hot-toast'

export function DashboardPage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showNew, setShowNew] = useState(false)
  const [title, setTitle] = useState('')
  const [wallW, setWallW] = useState(3000)
  const [wallH, setWallH] = useState(2400)

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list().then(r => r.data),
  })

  const createJob = useMutation({
    mutationFn: () => jobsApi.create({ title, wall_width_mm: wallW, wall_height_mm: wallH }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      navigate(`/jobs/${r.data.id}`)
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const deleteJob = useMutation({
    mutationFn: (id: string) => jobsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job deleted')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed to delete'),
  })

  const handleLogout = async () => {
    await authApi.logout()
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-wood-700">Wood Panel Designer</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{user?.email}</span>
          <button onClick={handleLogout} className="btn-secondary text-sm">Sign out</button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">My Jobs</h2>
          <button onClick={() => setShowNew(true)} className="btn-primary">+ New Job</button>
        </div>

        {showNew && (
          <div className="card p-5 mb-6">
            <h3 className="font-semibold mb-4">New Job</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="col-span-3">
                <label className="label">Job title</label>
                <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="Living room gallery wall" />
              </div>
              <div>
                <label className="label">Wall width (mm)</label>
                <input className="input" type="number" value={wallW} onChange={e => setWallW(+e.target.value)} />
              </div>
              <div>
                <label className="label">Wall height (mm)</label>
                <input className="input" type="number" value={wallH} onChange={e => setWallH(+e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => createJob.mutate()} disabled={!title || createJob.isPending} className="btn-primary">
                {createJob.isPending ? 'Creating…' : 'Create job'}
              </button>
              <button onClick={() => setShowNew(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="text-gray-400 text-sm">Loading…</div>
        ) : jobs?.length === 0 ? (
          <div className="card p-12 text-center text-gray-400">
            <p className="text-lg">No jobs yet.</p>
            <p className="text-sm mt-1">Create your first job to get started.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {jobs?.map(job => (
              <div key={job.id} className="card p-4 flex items-center gap-4 hover:shadow-md transition-shadow">
                <Link to={`/jobs/${job.id}`} className="flex-1 min-w-0">
                  <p className="font-medium truncate">{job.title}</p>
                  <p className="text-sm text-gray-500">{job.wall_width_mm} × {job.wall_height_mm} mm</p>
                </Link>
                <span className={`text-xs px-2 py-1 rounded-full font-medium shrink-0 ${STATUS_COLOURS[job.status]}`}>
                  {STATUS_LABELS[job.status]}
                </span>
                <span className="text-xs text-gray-400 shrink-0">{new Date(job.created_at).toLocaleDateString()}</span>
                <button
                  onClick={() => {
                    if (window.confirm(`Delete "${job.title}"? This cannot be undone.`)) {
                      deleteJob.mutate(job.id)
                    }
                  }}
                  className="btn-danger text-xs shrink-0"
                  disabled={deleteJob.isPending}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
