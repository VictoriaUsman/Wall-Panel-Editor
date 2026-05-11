import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useEditorStore } from '../../stores/editorStore'
import type { CanvasSize, Photo } from '../../types'
import { photosApi } from '../../api'
import toast from 'react-hot-toast'

interface Props {
  jobId: string
  readOnly?: boolean
  defaultCanvasSizeId?: string
  onchange?: () => void
}

export function PhotoTray({ jobId, readOnly = false, defaultCanvasSizeId, onchange }: Props) {
  const { photos, addPhoto, removePhoto, canvasSizes, panels } = useEditorStore()

  const onDrop = useCallback(async (files: File[]) => {
    for (const file of files) {
      const toastId = toast.loading(`Uploading ${file.name}…`)
      try {
        const { data: presign } = await photosApi.presign(jobId, file.name, file.type, file.size)

        // PUT directly to mock storage
        await fetch(presign.upload_url, {
          method: 'PUT',
          body: file,
          headers: presign.headers,
        })

        // Confirm
        let w: number | undefined, h: number | undefined
        const bitmap = await createImageBitmap(file).catch(() => null)
        if (bitmap) { w = bitmap.width; h = bitmap.height }

        const { data: photo } = await photosApi.confirm(jobId, presign.photo_id, {
          width_px: w, height_px: h, size_bytes: file.size,
        })
        addPhoto(photo)
        toast.success(`${file.name} uploaded`, { id: toastId })
      } catch (err: any) {
        toast.error(`Upload failed: ${err.message}`, { id: toastId })
      }
    }
  }, [jobId, addPhoto])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': [], 'image/png': [], 'image/webp': [] },
    disabled: readOnly,
    noClick: false,
  })

  const usedPhotoIds = new Set(panels.map(p => p.photo_id).filter(Boolean))

  return (
    <div className="w-48 flex flex-col gap-2 shrink-0">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Photos</h3>

      {!readOnly && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-3 text-center text-xs cursor-pointer transition-colors
            ${isDragActive ? 'border-wood-500 bg-wood-50' : 'border-gray-300 hover:border-wood-400'}`}
        >
          <input {...getInputProps()} />
          <span className="text-gray-500">Drop photos here or click to upload</span>
        </div>
      )}

      <div className="flex flex-col gap-1 overflow-y-auto max-h-[calc(100vh-300px)]">
        {photos.filter(p => p.upload_confirmed).map(photo => {
          const inUse = usedPhotoIds.has(photo.id)
          return (
            <div
              key={photo.id}
              draggable={!readOnly}
              onDragStart={e => {
                e.dataTransfer.setData('photo_id', photo.id)
                e.dataTransfer.setData('canvas_size_id', defaultCanvasSizeId || canvasSizes[0]?.id || '')
              }}
              className={`relative group rounded-lg overflow-hidden border cursor-grab
                ${inUse ? 'border-wood-400 opacity-60' : 'border-gray-200 hover:border-wood-400'}`}
            >
              {photo.url ? (
                <img src={photo.url} alt={photo.filename} className="w-full h-24 object-cover" />
              ) : (
                <div className="w-full h-24 bg-gray-100 flex items-center justify-center text-gray-400 text-xs">
                  {photo.filename}
                </div>
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
              {inUse && (
                <div className="absolute top-1 right-1 bg-wood-600 text-white text-xs px-1 rounded">in use</div>
              )}
              {!readOnly && (
                <button
                  onClick={async () => {
                    try {
                      await photosApi.delete(jobId, photo.id)
                    } catch (_) {}
                    removePhoto(photo.id)
                    onchange?.()
                  }}
                  className="absolute top-1 left-1 bg-red-600 text-white text-xs w-5 h-5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                >×</button>
              )}
              <div className="px-1 py-0.5 text-xs text-gray-600 truncate bg-white/90">{photo.filename}</div>
            </div>
          )
        })}
        {photos.filter(p => p.upload_confirmed).length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No photos yet</p>
        )}
      </div>
    </div>
  )
}
