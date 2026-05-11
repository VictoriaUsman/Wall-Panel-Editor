import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { jobsApi, authApi } from '../../api'
import { useAuthStore } from '../../stores/authStore'
import { STATUS_LABELS, STATUS_COLOURS } from '../../types'
import type { JobStatus, Job } from '../../types'
import toast from 'react-hot-toast'

const PIPELINE_ORDER: JobStatus[] = ['ARRANGING', 'PROOFING', 'APPROVED', 'PRINTED', 'SHIPPED', 'DRAFT', 'UPLOADED']

export function PipelinePage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list().then(r => r.data),
    refetchInterval: 30_000,
  })

  const handleLogout = async () => {
    await authApi.logout()
    logout()
    navigate('/login')
  }

  const grouped = PIPELINE_ORDER.reduce((acc, status) => {
    acc[status] = jobs?.filter(j => j.status === status) ?? []
    return acc
  }, {} as Record<JobStatus, Job[]>)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-wood-700 text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Operator Dashboard</h1>
          <p className="text-wood-100 text-sm">Wood Panel Wall Designer</p>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/operator/catalog" className="text-wood-100 hover:text-white text-sm">Canvas Catalog</Link>
          <span className="text-wood-200 text-sm">{user?.email}</span>
          <button onClick={handleLogout} className="btn-secondary text-sm">Sign out</button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <h2 className="text-lg font-semibold mb-6">Job Pipeline</h2>

        {isLoading ? (
          <div className="text-gray-400">Loading…</div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {PIPELINE_ORDER.map(status => {
              const group = grouped[status]
              if (!group.length && ['DRAFT', 'UPLOADED'].includes(status)) return null
              return (
                <div key={status}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOURS[status]}`}>
                      {STATUS_LABELS[status]}
                    </span>
                    <span className="text-xs text-gray-400">{group.length} job{group.length !== 1 ? 's' : ''}</span>
                  </div>
                  {group.length === 0 ? (
                    <div className="text-xs text-gray-300 pl-4">—</div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {group.map(job => (
                        <Link
                          key={job.id}
                          to={`/jobs/${job.id}`}
                          className="card p-4 hover:shadow-md transition-shadow"
                        >
                          <p className="font-medium text-sm">{job.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{job.wall_width_mm} × {job.wall_height_mm} mm</p>
                          <p className="text-xs text-gray-400 mt-1">
                            Updated {new Date(job.updated_at).toLocaleString()}
                          </p>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
