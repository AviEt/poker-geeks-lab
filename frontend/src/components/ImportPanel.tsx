import { useRef, useState } from 'react'
import { importFiles } from '../api/client'
import type { ImportResult } from '../api/client'

interface Props {
  onImportComplete?: () => void
}

export function ImportPanel({ onImportComplete }: Props = {}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFiles(Array.from(e.target.files ?? []))
    setResult(null)
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setLoading(true)
    setResult(null)
    try {
      const res = await importFiles(files)
      setResult(res)
      onImportComplete?.()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <input
        data-testid="file-input"
        ref={inputRef}
        type="file"
        multiple
        accept=".txt"
        onChange={handleChange}
      />
      <button onClick={handleUpload} disabled={files.length === 0 || loading}>
        Upload
      </button>
      {loading && <span data-testid="loading">Uploading…</span>}
      {result && (
        <div>
          <span>{result.imported} imported</span>
          {' · '}
          <span>{result.skipped} skipped</span>
          {result.errors.length > 0 && (
            <ul>
              {result.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
