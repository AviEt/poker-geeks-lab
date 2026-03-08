import { render, screen, waitFor, within } from '@testing-library/react'
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
  bb_per_100: 300,
  bb_per_100_adj: 300,
  pot_won: 0.30,
  rake_usd: 0.02,
  rake_bb: 0.4,
  pot_won_after_rake_usd: 0.28,
  pot_won_after_rake_bb100: 560,
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

  it('renders position and card columns using card chips', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByText('BTN')).toBeDefined()
      // Hole cards as chips
      expect(screen.getByText('A♠')).toBeDefined()
      expect(screen.getByText('K♥')).toBeDefined()
      // Flop chips
      expect(screen.getByText('T♠')).toBeDefined()
      expect(screen.getByText('9♦')).toBeDefined()
      expect(screen.getByText('2♣')).toBeDefined()
      // Turn / River chips
      expect(screen.getByText('5♥')).toBeDefined()
      expect(screen.getByText('J♣')).toBeDefined()
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

  it('renders new column headers', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getByText('BB/100')).toBeDefined()
      expect(screen.getByText('BB/100 Adj')).toBeDefined()
      expect(screen.getByText('Pot Won')).toBeDefined()
      expect(screen.getByText('Rake')).toBeDefined()
      expect(screen.getByText('After Rake')).toBeDefined()
    })
  })

  it('renders bb_per_100 and pot_won cell values', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    render(<HandsTable player="Hero" />)
    await waitFor(() => {
      expect(screen.getAllByText('300.00').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('$0.30')).toBeDefined()
      expect(screen.getByText('$0.02')).toBeDefined()
    })
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

  // ── Sorting ───────────────────────────────────────────────────────────────

  it('sorts rows by Net Won descending when column header is clicked', async () => {
    const hands = [
      { ...HAND, hand_id: '1', net_won: 0.15 },
      { ...HAND, hand_id: '2', net_won: -0.50 },
      { ...HAND, hand_id: '3', net_won: 1.00 },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('1'))
    await user.click(screen.getByRole('columnheader', { name: /net won/i }))

    const rows = screen.getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('+$1.00')).toBeDefined()
    expect(within(rows[1]).getByText('+$0.15')).toBeDefined()
    expect(within(rows[2]).getByText('-$0.50')).toBeDefined()
  })

  it('toggles sort to ascending on second click of same column', async () => {
    const hands = [
      { ...HAND, hand_id: '1', net_won: 0.15 },
      { ...HAND, hand_id: '2', net_won: -0.50 },
      { ...HAND, hand_id: '3', net_won: 1.00 },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('1'))
    await user.click(screen.getByRole('columnheader', { name: /net won/i }))
    await user.click(screen.getByRole('columnheader', { name: /net won/i }))

    const rows = screen.getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('-$0.50')).toBeDefined()
    expect(within(rows[2]).getByText('+$1.00')).toBeDefined()
  })

  it('sorts by position using canonical poker order BTN first', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'CO' },
      { ...HAND, hand_id: '2', hero_position: 'BTN' },
      { ...HAND, hand_id: '3', hero_position: 'SB' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('1'))
    await user.click(screen.getByRole('columnheader', { name: /position/i }))

    const rows = screen.getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('BTN')).toBeDefined()
    expect(within(rows[1]).getByText('CO')).toBeDefined()
    expect(within(rows[2]).getByText('SB')).toBeDefined()
  })

  it('sorts by hole cards alphabetically ascending', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_hole_cards: 'Kh Qd' },
      { ...HAND, hand_id: '2', hero_hole_cards: 'As Kh' },
      { ...HAND, hand_id: '3', hero_hole_cards: '2c 3d' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('1'))
    await user.click(screen.getByRole('columnheader', { name: /hole cards/i }))

    const rows = screen.getAllByRole('row').slice(1)
    // Ascending alpha: '2c 3d' < 'As Kh' < 'Kh Qd'
    // Use '3♦' (from '3d') to identify the '2c 3d' hand — '2c' also appears in the shared flop fixture
    expect(within(rows[0]).getByText('3♦')).toBeDefined()
    expect(within(rows[1]).getByText('A♠')).toBeDefined()
    expect(within(rows[2]).getByText('K♥')).toBeDefined()
  })

  it('shows sort direction indicator on active column', async () => {
    mockFetchHands.mockResolvedValue(makeResponse([HAND], 1))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('12345'))
    const header = screen.getByRole('columnheader', { name: /net won/i })
    expect(header.textContent).not.toMatch(/[↑↓]/)

    await user.click(header)
    expect(header.textContent).toMatch(/[↑↓]/)
  })

  // ── Filtering ─────────────────────────────────────────────────────────────

  it('renders position filter chips for available positions', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'BTN' },
      { ...HAND, hand_id: '2', hero_position: 'CO' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 2))
    render(<HandsTable player="Hero" />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'BTN' })).toBeDefined()
      expect(screen.getByRole('button', { name: 'CO' })).toBeDefined()
    })
  })

  it('filters rows by a single selected position', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'BTN' },
      { ...HAND, hand_id: '2', hero_position: 'CO' },
      { ...HAND, hand_id: '3', hero_position: 'BTN' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: 'BTN' }))

    expect(screen.getByText('1')).toBeDefined()
    expect(screen.getByText('3')).toBeDefined()
    expect(screen.queryByText('2')).toBeNull()
  })

  it('supports multi-select: BTN and CO both shown when both selected', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'BTN' },
      { ...HAND, hand_id: '2', hero_position: 'CO' },
      { ...HAND, hand_id: '3', hero_position: 'SB' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: 'CO' }))

    expect(screen.getByText('1')).toBeDefined()
    expect(screen.getByText('2')).toBeDefined()
    expect(screen.queryByText('3')).toBeNull()
  })

  it('deselecting a position chip removes that filter', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'BTN' },
      { ...HAND, hand_id: '2', hero_position: 'CO' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 2))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: 'BTN' }))
    expect(screen.queryByText('2')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'BTN' }))
    expect(screen.getByText('2')).toBeDefined()
  })

  it('filters by stakes multi-select', async () => {
    const hands = [
      { ...HAND, hand_id: '1', small_blind: 0.02, big_blind: 0.05 },
      { ...HAND, hand_id: '2', small_blind: 0.05, big_blind: 0.10 },
      { ...HAND, hand_id: '3', small_blind: 0.02, big_blind: 0.05 },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: '$0.02/$0.05' }))
    await user.click(screen.getByRole('button', { name: '$0.02/$0.05' }))

    expect(screen.getByText('1')).toBeDefined()
    expect(screen.getByText('3')).toBeDefined()
    expect(screen.queryByText('2')).toBeNull()
  })

  it('filters rows by hole cards text input', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_hole_cards: 'As Kh' },
      { ...HAND, hand_id: '2', hero_hole_cards: 'Qd Jc' },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 2))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByText('1'))
    await user.type(screen.getByRole('textbox', { name: /hole cards/i }), 'As')

    expect(screen.getByText('1')).toBeDefined()
    expect(screen.queryByText('2')).toBeNull()
  })

  it('position and stakes filters compose with AND logic', async () => {
    const hands = [
      { ...HAND, hand_id: '1', hero_position: 'BTN', small_blind: 0.02, big_blind: 0.05 },
      { ...HAND, hand_id: '2', hero_position: 'CO', small_blind: 0.02, big_blind: 0.05 },
      { ...HAND, hand_id: '3', hero_position: 'BTN', small_blind: 0.05, big_blind: 0.10 },
    ]
    mockFetchHands.mockResolvedValue(makeResponse(hands, 3))
    const user = userEvent.setup()
    render(<HandsTable player="Hero" />)

    await waitFor(() => screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: 'BTN' }))
    await user.click(screen.getByRole('button', { name: '$0.02/$0.05' }))

    expect(screen.getByText('1')).toBeDefined()
    expect(screen.queryByText('2')).toBeNull()
    expect(screen.queryByText('3')).toBeNull()
  })
})
