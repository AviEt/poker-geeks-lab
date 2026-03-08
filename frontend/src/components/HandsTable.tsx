import { useEffect, useState } from 'react'
import { fetchHands } from '../api/client'
import type { HandsResponse } from '../api/client'

const PAGE_SIZE = 20

interface Props {
  player: string
  onSelectHand?: (handId: string) => void
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

  return (
    <div>
      {data.hands.length === 0 ? (
        <p>No hands yet</p>
      ) : (
        <table>
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
            {data.hands.map(h => (
              <tr
                key={h.hand_id}
                onClick={() => onSelectHand?.(h.hand_id)}
                style={{ cursor: onSelectHand ? 'pointer' : undefined }}
              >
                <td>{h.hero_position ?? '—'}</td>
                <td>{h.hand_id}</td>
                <td>{h.hero_hole_cards ?? '—'}</td>
                <td>{h.flop ?? '—'}</td>
                <td>{h.turn ?? '—'}</td>
                <td>{h.river ?? '—'}</td>
                <td>${h.net_won.toFixed(2)}</td>
                <td>{h.bb_per_100.toFixed(2)}</td>
                <td>{h.bb_per_100_adj.toFixed(2)}</td>
                <td>${h.pot_won.toFixed(2)}</td>
                <td>${h.rake_usd.toFixed(2)}</td>
                <td>${h.pot_won_after_rake_usd.toFixed(2)}</td>
                <td>${h.small_blind}/${h.big_blind}</td>
                <td>{h.played_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <button onClick={onPrev} disabled={page <= 1}>Prev</button>
      <span> Page {page} of {totalPages} </span>
      <button onClick={onNext} disabled={page >= totalPages}>Next</button>
    </div>
  )
}
