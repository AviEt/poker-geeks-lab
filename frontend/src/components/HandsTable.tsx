import { useEffect, useState, useMemo } from 'react'
import { fetchHands } from '../api/client'
import type { HandsResponse, HandSummary } from '../api/client'
import { CardChips } from './CardChips'
import './HandsTable.css'

const PAGE_SIZE = 20

// Canonical position rank: higher = better seat; descending sort shows BTN first
const POSITION_ORDER: Record<string, number> = {
  BB: 0, SB: 1, UTG: 2, 'UTG+1': 3, MP: 4, HJ: 5, CO: 6, BTN: 7,
}

type SortKey = 'net_won' | 'bb_per_100' | 'bb_per_100_adj' | 'played_at' | 'hero_position' | 'hero_hole_cards' | null
type SortDir = 'asc' | 'desc'

// Columns that sort ascending on first click
const SORT_DEFAULT_ASC = new Set<SortKey>(['hero_hole_cards', 'played_at'])

interface Props {
  player: string
  onSelectHand?: (handId: string) => void
}

function netClass(net: number) {
  if (net > 0.001) return 'col-profit'
  if (net < -0.001) return 'col-loss'
  return 'col-muted'
}

function netCardClass(net: number) {
  if (net > 0.001) return 'hand-card__net--profit'
  if (net < -0.001) return 'hand-card__net--loss'
  return 'hand-card__net--neutral'
}

function formatNet(net: number) {
  const sign = net >= 0 ? '+' : '-'
  return `${sign}$${Math.abs(net).toFixed(2)}`
}

function formatStakes(h: HandSummary) {
  return `$${h.small_blind}/$${h.big_blind}`
}

function compareHands(a: HandSummary, b: HandSummary, key: SortKey, dir: SortDir): number {
  if (!key) return 0
  let cmp = 0
  if (key === 'hero_position') {
    const ao = POSITION_ORDER[a.hero_position ?? ''] ?? 99
    const bo = POSITION_ORDER[b.hero_position ?? ''] ?? 99
    cmp = ao - bo
  } else if (key === 'hero_hole_cards') {
    cmp = (a.hero_hole_cards ?? '').localeCompare(b.hero_hole_cards ?? '')
  } else if (key === 'played_at') {
    cmp = (a.played_at ?? '').localeCompare(b.played_at ?? '')
  } else {
    cmp = (a[key] as number) - (b[key] as number)
  }
  return dir === 'asc' ? cmp : -cmp
}

interface SortHeaderProps {
  label: string
  sortKey: SortKey
  active: SortKey
  dir: SortDir
  onClick: (k: SortKey) => void
}

function SortHeader({ label, sortKey, active, dir, onClick }: SortHeaderProps) {
  const isActive = active === sortKey
  return (
    <th
      role="columnheader"
      onClick={() => onClick(sortKey)}
      className={`sort-header${isActive ? ' sort-header--active' : ''}`}
      style={{ cursor: 'pointer' }}
    >
      {label}{isActive ? (dir === 'desc' ? ' ↓' : ' ↑') : ''}
    </th>
  )
}

export function HandsTable({ player, onSelectHand }: Props) {
  const [data, setData] = useState<HandsResponse | null>(null)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<SortKey>(null)
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [positionFilter, setPositionFilter] = useState<string[]>([])
  const [stakesFilter, setStakesFilter] = useState<string[]>([])
  const [holeCardsFilter, setHoleCardsFilter] = useState('')

  useEffect(() => {
    fetchHands(player, page, PAGE_SIZE).then(setData)
  }, [player, page])

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const onPrev = () => setPage(p => p - 1)
  const onNext = () => setPage(p => p + 1)

  function handleSortClick(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortKey(key)
      setSortDir(SORT_DEFAULT_ASC.has(key) ? 'asc' : 'desc')
    }
  }

  function toggleFilter<T>(arr: T[], value: T): T[] {
    return arr.includes(value) ? arr.filter(x => x !== value) : [...arr, value]
  }

  const allHands = data?.hands ?? []

  const availablePositions = useMemo(() => {
    const seen = new Set<string>()
    allHands.forEach(h => { if (h.hero_position) seen.add(h.hero_position) })
    return [...seen].sort((a, b) => (POSITION_ORDER[a] ?? 99) - (POSITION_ORDER[b] ?? 99))
  }, [allHands])

  const availableStakes = useMemo(() => {
    const seen = new Set<string>()
    allHands.forEach(h => seen.add(formatStakes(h)))
    return [...seen].sort()
  }, [allHands])

  const visibleHands = useMemo(() => {
    let hands = [...allHands]

    if (positionFilter.length > 0) {
      hands = hands.filter(h => positionFilter.includes(h.hero_position ?? ''))
    }
    if (stakesFilter.length > 0) {
      hands = hands.filter(h => stakesFilter.includes(formatStakes(h)))
    }
    if (holeCardsFilter.trim()) {
      const q = holeCardsFilter.trim().toLowerCase()
      hands = hands.filter(h => (h.hero_hole_cards ?? '').toLowerCase().includes(q))
    }
    if (sortKey) {
      hands.sort((a, b) => compareHands(a, b, sortKey, sortDir))
    }
    return hands
  }, [allHands, positionFilter, stakesFilter, holeCardsFilter, sortKey, sortDir])

  if (!data) return null

  if (data.hands.length === 0) {
    return (
      <div className="hands-empty">
        <div className="hands-empty__icon">🃏</div>
        <div>No hands yet — import some hand histories first</div>
      </div>
    )
  }

  return (
    <div className="hands-table-wrap">
      {/* ── Filter bar ── */}
      <div className="hands-filter-bar">
        <div className="filter-group">
          <span className="filter-label">Position</span>
          <div className="filter-chips">
            {availablePositions.map(pos => (
              <button
                key={pos}
                aria-label={pos}
                className={`filter-chip${positionFilter.includes(pos) ? ' filter-chip--active' : ''}`}
                onClick={() => setPositionFilter(prev => toggleFilter(prev, pos))}
              >
                {pos}·
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <span className="filter-label">Stakes</span>
          <div className="filter-chips">
            {availableStakes.map(s => (
              <button
                key={s}
                aria-label={s}
                className={`filter-chip${stakesFilter.includes(s) ? ' filter-chip--active' : ''}`}
                onClick={() => setStakesFilter(prev => toggleFilter(prev, s))}
              >
                {s}·
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <label className="filter-label" htmlFor="hole-cards-filter">Hole Cards</label>
          <input
            id="hole-cards-filter"
            type="text"
            className="filter-input"
            placeholder="e.g. As"
            value={holeCardsFilter}
            onChange={e => setHoleCardsFilter(e.target.value)}
            aria-label="Hole cards filter"
          />
        </div>
      </div>

      {/* ── Desktop table ── */}
      <div className="hands-table-container">
        <table className="hands-table">
          <thead>
            <tr>
              <SortHeader label="Position" sortKey="hero_position" active={sortKey} dir={sortDir} onClick={handleSortClick} />
              <th>Hand ID</th>
              <SortHeader label="Hole Cards" sortKey="hero_hole_cards" active={sortKey} dir={sortDir} onClick={handleSortClick} />
              <th>Flop</th>
              <th>Turn</th>
              <th>River</th>
              <SortHeader label="Net Won" sortKey="net_won" active={sortKey} dir={sortDir} onClick={handleSortClick} />
              <SortHeader label="BB/100" sortKey="bb_per_100" active={sortKey} dir={sortDir} onClick={handleSortClick} />
              <SortHeader label="BB/100 Adj" sortKey="bb_per_100_adj" active={sortKey} dir={sortDir} onClick={handleSortClick} />
              <th>Pot Won</th>
              <th>Rake</th>
              <th>After Rake</th>
              <th>Stakes</th>
              <SortHeader label="Date" sortKey="played_at" active={sortKey} dir={sortDir} onClick={handleSortClick} />
            </tr>
          </thead>
          <tbody>
            {visibleHands.map((h: HandSummary) => (
              <tr
                key={h.hand_id}
                onClick={() => onSelectHand?.(h.hand_id)}
              >
                <td className="col-muted">{h.hero_position ?? '—'}</td>
                <td className="col-muted col-num">{h.hand_id}</td>
                <td className="col-cards"><CardChips cards={h.hero_hole_cards} /></td>
                <td className="col-cards col-muted"><CardChips cards={h.flop} /></td>
                <td className="col-cards col-muted"><CardChips cards={h.turn} /></td>
                <td className="col-cards col-muted"><CardChips cards={h.river} /></td>
                <td className={netClass(h.net_won)}>{formatNet(h.net_won)}</td>
                <td className="col-num">{h.bb_per_100.toFixed(2)}</td>
                <td className="col-num">{h.bb_per_100_adj.toFixed(2)}</td>
                <td className="col-num col-muted">${h.pot_won.toFixed(2)}</td>
                <td className="col-num col-muted">${h.rake_usd.toFixed(2)}</td>
                <td className="col-num col-muted">${h.pot_won_after_rake_usd.toFixed(2)}</td>
                <td className="col-muted">{formatStakes(h)}</td>
                <td className="col-muted">{h.played_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Mobile card list ── */}
      <div className="hands-mobile-list" aria-hidden="true">
        {visibleHands.map((h: HandSummary) => (
          <div
            key={h.hand_id}
            className="hand-card"
            onClick={() => onSelectHand?.(h.hand_id)}
          >
            <div className="hand-card__left">
              <div className="hand-card__meta">
                {`${h.hero_position ?? '—'} · ${formatStakes(h)}`}
              </div>
              <div className="hand-card__date">{h.played_at}</div>
            </div>
            <div className="hand-card__right">
              <div className={`hand-card__net ${netCardClass(h.net_won)}`}>{formatNet(h.net_won)}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Pagination ── */}
      <div className="hands-pagination">
        <button className="pagination-btn" onClick={onPrev} disabled={page <= 1} aria-label="Prev">←</button>
        <span className="pagination-info">Page {page} of {totalPages}</span>
        <button className="pagination-btn" onClick={onNext} disabled={page >= totalPages} aria-label="Next">→</button>
      </div>
    </div>
  )
}
