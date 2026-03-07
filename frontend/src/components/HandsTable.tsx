import { useEffect, useState } from 'react'
import { fetchHands } from '../api/client'
import type { HandsResponse } from '../api/client'

const PAGE_SIZE = 20

interface Props {
  player: string
}

export function HandsTable({ player }: Props) {
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
              <th>Hand ID</th>
              <th>Date</th>
              <th>Table</th>
              <th>Game</th>
              <th>Stakes</th>
            </tr>
          </thead>
          <tbody>
            {data.hands.map(h => (
              <tr key={h.hand_id}>
                <td>{h.hand_id}</td>
                <td>{h.played_at}</td>
                <td>{h.table_name}</td>
                <td>{h.game_type}</td>
                <td>${h.small_blind}/${h.big_blind}</td>
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
