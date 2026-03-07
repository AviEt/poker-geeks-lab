import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { ImportPanel } from '../components/ImportPanel'
import * as client from '../api/client'

vi.mock('../api/client')

const mockImport = vi.spyOn(client, 'importFiles')

describe('ImportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders a file input and upload button', () => {
    render(<ImportPanel />)
    expect(screen.getByTestId('file-input')).toBeDefined()
    expect(screen.getByRole('button', { name: /upload/i })).toBeDefined()
  })

  it('upload button is disabled when no files are selected', () => {
    render(<ImportPanel />)
    expect(screen.getByRole('button', { name: /upload/i })).toBeDisabled()
  })

  it('calls importFiles with the selected files on upload', async () => {
    mockImport.mockResolvedValue({ imported: 3, skipped: 0, errors: [] })
    const user = userEvent.setup()
    render(<ImportPanel />)

    const file = new File(['content'], 'hands.txt', { type: 'text/plain' })
    await user.upload(screen.getByTestId('file-input'), file)
    await user.click(screen.getByRole('button', { name: /upload/i }))

    expect(mockImport).toHaveBeenCalledWith([file])
  })

  it('shows imported and skipped counts on success', async () => {
    mockImport.mockResolvedValue({ imported: 10, skipped: 2, errors: [] })
    const user = userEvent.setup()
    render(<ImportPanel />)

    await user.upload(screen.getByTestId('file-input'), new File(['x'], 'a.txt'))
    await user.click(screen.getByRole('button', { name: /upload/i }))

    await waitFor(() => {
      expect(screen.getByText(/10 imported/i)).toBeDefined()
      expect(screen.getByText(/2 skipped/i)).toBeDefined()
    })
  })

  it('shows error messages when errors are present', async () => {
    mockImport.mockResolvedValue({ imported: 0, skipped: 0, errors: ['bad.txt: parse error'] })
    const user = userEvent.setup()
    render(<ImportPanel />)

    await user.upload(screen.getByTestId('file-input'), new File(['x'], 'bad.txt'))
    await user.click(screen.getByRole('button', { name: /upload/i }))

    await waitFor(() => {
      expect(screen.getByText(/parse error/i)).toBeDefined()
    })
  })

  it('shows loading indicator while uploading', async () => {
    let resolve: (v: client.ImportResult) => void
    mockImport.mockReturnValue(new Promise(r => { resolve = r }))
    const user = userEvent.setup()
    render(<ImportPanel />)

    await user.upload(screen.getByTestId('file-input'), new File(['x'], 'a.txt'))
    await user.click(screen.getByRole('button', { name: /upload/i }))

    expect(screen.getByTestId('loading')).toBeDefined()
    resolve!({ imported: 1, skipped: 0, errors: [] })
  })
})
