import { useEffect, useState } from 'react'
import { fetchHands } from '../api/client'
import type { HandsResponse, HandSummary } from '../api/client'
import './HandsTable.css'

const PAGE_SIZE = 20

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
  const sign = net >= 0 ? '+' : ''
  return `${sign}$${net.toFixed(2)}`
}

export function HandsTable({ player, onSelectHand }: Props) {
  const [data, setData] = useState<HandsResponse | null>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetchHands(player, page, PAGE_SIZE).then(setData)
  }, [player, page])

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const onPrev = () => setPage(p => p - 1)
  const onNext = () => setPage(p => p + 1)

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
      {/* ── Desktop table ── */}
      <div className="hands-table-container">
        <table className="hands-table">
          <thead>
            <tr>
              <th>Position</th>
              <th>Hand ID</th>
              <th>Hole Cards</th>
              <th>Flop</th>
              <th>Turn</th>
              <th>River</th>
              <th>Net Won</th>
              <th>BB/100</th>
              <th>BB/100 Adj</th>
              <th>Pot Won</th>
              <th>Rake</th>
              <th>After Rake</th>
              <th>Stakes</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {data.hands.map((h: HandSummary) => (
              <tr
                key={h.hand_id}
                onClick={() => onSelectHand?.(h.hand_id)}
              >
                <td className="col-muted">{h.hero_position ?? '—'}</td>
                <td className="col-muted col-num">{h.hand_id}</td>
                <td className="col-cards">{h.hero_hole_cards ?? '—'}</td>
                <td className="col-cards col-muted">{h.flop ?? '—'}</td>
                <td className="col-cards col-muted">{h.turn ?? '—'}</td>
                <td className="col-cards col-muted">{h.river ?? '—'}</td>
                <td className={netClass(h.net_won)}>{formatNet(h.net_won)}</td>
                <td className="col-num">{h.bb_per_100.toFixed(2)}</td>
                <td className="col-num">{h.bb_per_100_adj.toFixed(2)}</td>
                <td className="col-num col-muted">${h.pot_won.toFixed(2)}</td>
                <td className="col-num col-muted">${h.rake_usd.toFixed(2)}</td>
                <td className="col-num col-muted">${h.pot_won_after_rake_usd.toFixed(2)}</td>
                <td className="col-muted">${h.small_blind}/${h.big_blind}</td>
                <td className="col-muted">{h.played_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Mobile card list ── */}
      <div className="hands-mobile-list" aria-hidden="true">
        {data.hands.map((h: HandSummary) => (
          <div
            key={h.hand_id}
            className="hand-card"
            onClick={() => onSelectHand?.(h.hand_id)}
          >
            <div className="hand-card__left">
              <div className="hand-card__meta">
                {`${h.hero_position ?? '—'} · $${h.small_blind}/${h.big_blind}`}
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
