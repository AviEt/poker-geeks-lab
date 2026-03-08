import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { HandDetail } from '../components/HandDetail'
import * as client from '../api/client'

vi.mock('../api/client')

const mockFetchHandDetail = vi.spyOn(client, 'fetchHandDetail')

const DETAIL: client.HandDetail = {
  hand_id: '12345',
  played_at: '2023-12-05T10:00:00',
  table_name: 'RushAndCash',
  game_type: 'NLHoldem',
  small_blind: 0.02,
  big_blind: 0.05,
  pot: 0.25,
  rake: 0.01,
  hero_name: 'Hero',
  players: [
    { name: 'Hero', seat: 1, stack: 5.0, position: 'BTN', hole_cards: 'As Kh', net_won: 0.15 },
    { name: 'Villain', seat: 2, stack: 5.0, position: 'BB', hole_cards: null, net_won: -0.15 },
  ],
  streets: [
    {
      name: 'preflop',
      cards: null,
      actions: [
        { player: 'Villain', action: 'post_bb', amount: 0.05, is_all_in: false },
        { player: 'Hero', action: 'raise', amount: 0.15, is_all_in: false },
        { player: 'Villain', action: 'call', amount: 0.10, is_all_in: false },
      ],
    },
    {
      name: 'flop',
      cards: 'Ts 9d 2c',
      actions: [
        { player: 'Villain', action: 'check', amount: null, is_all_in: false },
        { player: 'Hero', action: 'bet', amount: 0.20, is_all_in: false },
        { player: 'Villain', action: 'fold', amount: null, is_all_in: false },
      ],
    },
  ],
}

describe('HandDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches hand detail on mount', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => expect(mockFetchHandDetail).toHaveBeenCalledWith('Hero', '12345'))
  })

  it('renders hand id', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText(/12345/)).toBeDefined())
  })

  it('renders street tabs', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => {
      expect(screen.getByTestId('tab-preflop')).toBeDefined()
      expect(screen.getByTestId('tab-flop')).toBeDefined()
    })
  })

  it('shows preflop actions by default', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => {
      expect(screen.getByText(/Hero raise \$0\.15/)).toBeDefined()
    })
  })

  it('switches to flop actions when flop tab is clicked', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    const user = userEvent.setup()
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => screen.getByTestId('tab-flop'))
    await user.click(screen.getByTestId('tab-flop'))
    await waitFor(() => {
      expect(screen.getByText(/Hero bet \$0\.20/)).toBeDefined()
    })
  })

  it('renders player table', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    render(<HandDetail player="Hero" handId="12345" onClose={() => {}} />)
    await waitFor(() => {
      expect(screen.getAllByText('Hero').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Villain').length).toBeGreaterThan(0)
    })
  })

  it('calls onClose when Close button is clicked', async () => {
    mockFetchHandDetail.mockResolvedValue(DETAIL)
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<HandDetail player="Hero" handId="12345" onClose={onClose} />)
    await waitFor(() => screen.getByRole('button', { name: /close/i }))
    await user.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
