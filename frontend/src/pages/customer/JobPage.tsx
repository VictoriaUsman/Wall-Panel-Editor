import React, { useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, panelsApi, photosApi, catalogApi, pdfApi } from '../../api'
import { useEditorStore } from '../../stores/editorStore'
import { useAuthStore } from '../../stores/authStore'
import { WallEditor } from '../../components/editor/WallEditor'
import { PhotoTray } from '../../components/editor/PhotoTray'
import { PanelControls } from '../../components/editor/PanelControls'
import { STATUS_LABELS, STATUS_COLOURS } from '../../types'
import toast from 'react-hot-toast'

const AUTOSAVE_DELAY_MS = 800

export function JobPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const { panels, setInitial } = useEditorStore()
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const initializedRef = useRef(false)

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!).then(r => r.data),
    enabled: !!jobId,
  })

  const { data: photos } = useQuery({
    queryKey: ['photos', jobId],
    queryFn: () => photosApi.list(jobId!).then(r => r.data),
    enabled: !!jobId,
  })

  const { data: panelsData } = useQuery({
    queryKey: ['panels', jobId],
    queryFn: () => panelsApi.list(jobId!).then(r => r.data),
    enabled: !!jobId,
  })

  const { data: catalog } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => catalogApi.list().then(r => r.data),
  })

  useEffect(() => {
    if (!initializedRef.current && panelsData && catalog && photos) {
      const editorPanels = panelsData.map(p => ({
        id: p.id, canvas_size_id: p.canvas_size_id, photo_id: p.photo_id,
        x_mm: p.x_mm, y_mm: p.y_mm, rotation_deg: p.rotation_deg, sort_order: p.sort_order,
      }))
      setInitial(editorPanels, catalog, photos)
      initializedRef.current = true
    }
  }, [panelsData, catalog, photos, setInitial])

  // Undo/redo keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        useEditorStore.getState().undo()
        triggerAutosave()
      }
      if ((e.metaKey || e.ctrlKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
        e.preventDefault()
        useEditorStore.getState().redo()
        triggerAutosave()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const saveMutation = useMutation({
    mutationFn: (ps: typeof panels) => panelsApi.batchSave(jobId!, ps),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['panels', jobId] })
    },
    onError: () => toast.error('Auto-save failed'),
  })

  const triggerAutosave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      saveMutation.mutate(useEditorStore.getState().panels)
    }, AUTOSAVE_DELAY_MS)
  }, [saveMutation])

  const transitionMutation = useMutation({
    mutationFn: (to: string) => jobsApi.transition(jobId!, to),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job', jobId] })
      toast.success('Status updated')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  if (jobLoading || !job) return <div className="p-8 text-gray-400">Loading…</div>

  const isReadOnly = job.status === 'PROOFING' && !user?.is_operator
  const isFinished = ['APPROVED', 'PRINTED', 'SHIPPED'].includes(job.status)
  const canApprove = job.status === 'PROOFING' && !user?.is_operator
  const showPdfs = ['PROOFING', 'APPROVED', 'PRINTED', 'SHIPPED'].includes(job.status)

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
        <Link to={user?.is_operator ? '/operator' : '/dashboard'} className="text-gray-400 hover:text-gray-600 text-sm">
          ← Back
        </Link>
        <h1 className="font-bold text-wood-700 flex-1">{job.title}</h1>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLOURS[job.status]}`}>
          {STATUS_LABELS[job.status]}
        </span>
        {saveMutation.isPending && <span className="text-xs text-gray-400">Saving…</span>}

        {/* Action buttons — customer status progression */}
        {!user?.is_operator && job.status === 'DRAFT' && (
          <button onClick={() => transitionMutation.mutate('UPLOADED')} className="btn-secondary text-sm">
            Mark photos uploaded
          </button>
        )}
        {!user?.is_operator && job.status === 'UPLOADED' && (
          <button onClick={() => transitionMutation.mutate('ARRANGING')} className="btn-secondary text-sm">
            Start arranging
          </button>
        )}
        {!user?.is_operator && job.status === 'ARRANGING' && (
          <button onClick={() => transitionMutation.mutate('PROOFING')} className="btn-primary text-sm">
            Submit for review
          </button>
        )}
        {canApprove && (
          <>
            <button onClick={() => transitionMutation.mutate('ARRANGING')} className="btn-secondary text-sm">
              Request changes
            </button>
            <button onClick={() => transitionMutation.mutate('APPROVED')} className="btn-primary text-sm">
              Approve
            </button>
          </>
        )}

        {/* Operator actions */}
        {user?.is_operator && job.status === 'ARRANGING' && (
          <button onClick={() => transitionMutation.mutate('PROOFING')} className="btn-primary text-sm">
            Send proof
          </button>
        )}
        {user?.is_operator && job.status === 'APPROVED' && (
          <button onClick={() => transitionMutation.mutate('PRINTED')} className="btn-primary text-sm">
            Mark printed
          </button>
        )}
        {user?.is_operator && job.status === 'PRINTED' && (
          <button onClick={() => transitionMutation.mutate('SHIPPED')} className="btn-primary text-sm">
            Mark shipped
          </button>
        )}

        {/* PDF downloads */}
        {showPdfs && (
          <>
            <a href={pdfApi.templateUrl(job.id)} download className="btn-secondary text-sm">
              ↓ Hanging template
            </a>
            <a href={pdfApi.referenceUrl(job.id)} download className="btn-secondary text-sm">
              ↓ Reference sheet
            </a>
          </>
        )}
        {user?.is_operator && isFinished && (
          <a href={pdfApi.printMastersUrl(job.id)} download className="btn-primary text-sm">
            ↓ Print masters
          </a>
        )}
      </header>

      {/* Editor */}
      <div className="flex flex-1 gap-3 p-4 overflow-hidden" style={{ height: 'calc(100vh - 64px)' }}>
        <PhotoTray
          jobId={job.id}
          readOnly={isReadOnly || isFinished}
          defaultCanvasSizeId={catalog?.[0]?.id}
          onchange={triggerAutosave}
        />

        <WallEditor
          wallWidthMm={job.wall_width_mm}
          wallHeightMm={job.wall_height_mm}
          readOnly={isReadOnly || isFinished}
          onchange={triggerAutosave}
        />

        <PanelControls readOnly={isReadOnly || isFinished} onchange={triggerAutosave} />
      </div>
    </div>
  )
}
