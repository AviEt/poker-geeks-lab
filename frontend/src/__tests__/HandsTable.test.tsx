import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { HandsTable } from '../components/HandsTable'
import * as client from '../api/client'

vi.mock('../api/client')

const mockFetchHands = vi.spyOn(client, 'fetchHands')

const makeResponse = (hands: client.HandSummary[], total: number, page = 1): client.HandsResponse => ({
  player: 'Hero',
  total,
  page,
  page_size: 20,
  hands,
})

const HAND: client.HandSummary = {
  hand_id: '12345',
  played_at: '2023-12-05T10:00:00',
  table_name: 'RushAndCash15083753',
  game_type: 'NLHoldem',
  small_blind: 0.02,
  big_blind: 0.05,
  hero_name: 'Hero',
  hero_position: 'BTN',
  hero_hole_cards: 'As Kh',
  flop: 'Ts 9d 2c',
  turn: '5h',
  river: 'Jc',
  net_won: 0.15,
}

describe('HandsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls fetchHands on mount with player and page 1', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([], 0))
    render(<HandsTable player="Hero" />)
    await waitFor(() => expect(mockFetchHands).toHaveBeenCalledWith('Hero', 1, 20))
  })

  it('renders a row for each hand', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND, { ...HAND, hand_id: '99999' }], 2))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByText('12345')).toBeDefined()
      expect(screen.getByText('99999')).toBeDefined()
    })
  })

  it('shows "No hands yet" when list is empty', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([], 0))
    render(<HandsTable player="Hero" />)
    await waitFor(() => expect(screen.getByText(/no hands yet/i)).toBeDefined())
  })

  it('Prev button is disabled on page 1', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1, 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /prev/i })).toBeDisabled()
    })
  })

  it('Next button is disabled on the last page', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1, 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next/i })).toBeDisabled()
    })
  })

  it('clicking Next increments page and refetches', async () => {
    const page1Hands = Array.from({ length: 20 }, (_, i) => ({ ...HAND, hand_id: `p1-${i}` }))
    mockFetchHands.mockResolvedValue(makeResponse(page1Hands, 50, 1))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: /next/i }))
    await user.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() => expect(mockFetchHands).toHaveBeenCalledWith('Hero', 2, 20))
  })

  it('renders position, hole cards, and board columns', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByText('BTN')).toBeDefined()
      expect(screen.getByText('As Kh')).toBeDefined()
      expect(screen.getByText('Ts 9d 2c')).toBeDefined()
      expect(screen.getByText('5h')).toBeDefined()
      expect(screen.getByText('Jc')).toBeDefined()
    })
  })

  it('calls onSelectHand when a row is clicked', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<HandsTable player="Hero" onSelectHand={onSelect} />)
    await waitFor(() => screen.getByText('12345'))
    await user.click(screen.getByText('12345'))
    expect(onSelect).toHaveBeenCalledWith('12345')
  })

  it('clicking Prev decrements page and refetches', async () => {
    const page1Hands = Array.from({ length: 20 }, (_, i) => ({ ...HAND, hand_id: `p1-${i}` }))
    const page2Hands = Array.from({ length: 20 }, (_, i) => ({ ...HAND, hand_id: `p2-${i}` }))
    mockFetchHands
      .mockResolvedValueOnce(makeResponse(page1Hands, 50, 1))
      .mockResolvedValue(makeResponse(page2Hands, 50, 2))

    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: /next/i }))
    await user.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() => screen.getByRole('button', { name: /prev/i }))
    await user.click(screen.getByRole('button', { name: /prev/i }))

    await waitFor(() => expect(mockFetchHands).toHaveBeenCalledWith('Hero', 1, 20))
  })
})
