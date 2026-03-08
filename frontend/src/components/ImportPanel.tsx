import { useRef, useState } from 'react'
import { importFiles } from '../api/client'
import type { ImportResult } from '../api/client'
import './ImportPanel.css'

interface Props {
  onImportComplete?: () => void
}

export function ImportPanel({ onImportComplete }: Props = {}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (incoming: FileList | null) => {
    if (!incoming) return
    const txt = Array.from(incoming).filter(f => f.name.endsWith('.txt'))
    setFiles(txt)
    setResult(null)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleZoneClick = () => inputRef.current?.click()

  const handleUpload = async () => {
    if (files.length === 0) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await importFiles(files)
      setResult(res)
      setFiles([])
      if (inputRef.current) inputRef.current.value = ''
      onImportComplete?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="import-panel">
      {/* Drop zone */}
      <div
        className={`import-dropzone ${dragOver ? 'import-dropzone--drag-over' : ''}`}
        onClick={handleZoneClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && handleZoneClick()}
      >
        <div className="import-dropzone__icon">⬆</div>
        <div className="import-dropzone__title">
          {files.length > 0
            ? `${files.length} file${files.length > 1 ? 's' : ''} selected`
            : 'Drop .txt hand history files here'}
        </div>
        <div className="import-dropzone__sub">or click to browse</div>
      </div>

      <input
        data-testid="file-input"
        ref={inputRef}
        type="file"
        multiple
        accept=".txt"
        onChange={handleChange}
        className="import-file-input"
      />

      {/* Actions */}
      <div className="import-actions">
        <button
          className="import-btn import-btn--primary"
          onClick={handleUpload}
          disabled={files.length === 0 || loading}
        >
          Upload
        </button>

        {files.length > 0 && !loading && (
          <span className="import-file-badge">{files.length} file{files.length > 1 ? 's' : ''}</span>
        )}

        {loading && (
          <div className="import-loading" data-testid="loading">
            <div className="import-spinner" />
            Uploading…
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="import-errors">
          <li className="import-error-item">{error}</li>
        </div>
      )}

      {/* Result */}
      {result && (
        <div>
          <div className="import-result">
            {result.imported > 0 && (
              <span className="import-badge import-badge--success">
                ✓ {result.imported} imported
              </span>
            )}
            {result.skipped > 0 && (
              <span className="import-badge import-badge--warn">
                ⚠ {result.skipped} skipped
              </span>
            )}
          </div>
          {result.errors.length > 0 && (
            <ul className="import-errors">
              {result.errors.map((e, i) => (
                <li key={i} className="import-error-item">{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
