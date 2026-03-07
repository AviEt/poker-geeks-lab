import { render, screen, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { StatsPanel } from '../components/StatsPanel'
import * as client from '../api/client'

vi.mock('../api/client')

const mockFetchStats = vi.spyOn(client, 'fetchStats')

const STATS: client.PlayerStats = {
  player: 'Hero',
  hands: 100,
  vpip: 24.5,
  pfr: 18.2,
  bb_per_100: 5.32,
  bb_per_100_adjusted: 5.10,
}

describe('StatsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls fetchStats on mount with the player name', async () => {
    mockFetchStats.mockResolvedValue(STATS)
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(mockFetchStats).toHaveBeenCalledWith('Hero'))
  })

  it('displays VPIP after loading', async () => {
    mockFetchStats.mockResolvedValue(STATS)
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(screen.getByTestId('vpip')).toHaveTextContent('24.5'))
  })

  it('displays PFR after loading', async () => {
    mockFetchStats.mockResolvedValue(STATS)
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(screen.getByTestId('pfr')).toHaveTextContent('18.2'))
  })

  it('displays BB/100 after loading', async () => {
    mockFetchStats.mockResolvedValue(STATS)
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(screen.getByTestId('bb100')).toHaveTextContent('5.32'))
  })

  it('displays BB/100 adjusted after loading', async () => {
    mockFetchStats.mockResolvedValue(STATS)
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(screen.getByTestId('bb100adj')).toHaveTextContent('5.10'))
  })

  it('shows loading indicator while fetching', () => {
    mockFetchStats.mockReturnValue(new Promise(() => {}))
    render(<StatsPanel player="Hero" />)
    expect(screen.getByTestId('loading')).toBeDefined()
  })

  it('shows 0 hands when response has no hands', async () => {
    mockFetchStats.mockResolvedValue({ ...STATS, hands: 0 })
    render(<StatsPanel player="Hero" />)
    await waitFor(() => expect(screen.getByTestId('hands')).toHaveTextContent('0'))
  })
})
