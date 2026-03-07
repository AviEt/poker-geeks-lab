import { useEffect, useState } from 'react'
import { fetchHandDetail } from '../api/client'
import type { HandDetail as HandDetailType, HandStreet } from '../api/client'

interface Props {
  player: string
  handId: string
  onClose: () => void
}

function formatAction(a: { player: string; action: string; amount: number | null; is_all_in: boolean }): string {
  const label = a.action.replace('_', ' ')
  let text = `${a.player} ${label}`
  if (a.amount != null) text += ` $${a.amount.toFixed(2)}`
  if (a.is_all_in) text += ' (all-in)'
  return text
}

function StreetSection({ street }: { street: HandStreet }) {
  const title = street.name.charAt(0).toUpperCase() + street.name.slice(1)
  return (
    <div style={{ marginBottom: '1rem' }}>
      <h4 style={{ margin: '0 0 0.25rem' }}>
        {title}
        {street.cards ? ` [${street.cards}]` : ''}
      </h4>
      <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
        {street.actions.map((a, i) => (
          <li key={i}>{formatAction(a)}</li>
        ))}
      </ul>
    </div>
  )
}

export function HandDetail({ player, handId, onClose }: Props) {
  const [data, setData] = useState<HandDetailType | null>(null)
  const [activeStreet, setActiveStreet] = useState<string | null>(null)

  useEffect(() => {
    fetchHandDetail(player, handId).then(d => {
      setData(d)
      if (d.streets.length > 0) setActiveStreet(d.streets[0].name)
    })
  }, [player, handId])

  if (!data) return <p>Loading…</p>

  const active = data.streets.find(s => s.name === activeStreet)

  return (
    <div data-testid="hand-detail">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Hand #{data.hand_id}</h3>
        <button onClick={onClose}>Close</button>
      </div>
      <p>
        {data.table_name} — ${data.small_blind}/${data.big_blind} — Pot: ${data.pot.toFixed(2)}
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {data.streets.map(s => (
          <button
            key={s.name}
            onClick={() => setActiveStreet(s.name)}
            style={{
              fontWeight: activeStreet === s.name ? 'bold' : 'normal',
              textDecoration: activeStreet === s.name ? 'underline' : 'none',
            }}
            data-testid={`tab-${s.name}`}
          >
            {s.name.charAt(0).toUpperCase() + s.name.slice(1)}
            {s.cards ? ` [${s.cards}]` : ''}
          </button>
        ))}
      </div>

      {active && (
        <div data-testid="street-actions">
          <ul style={{ paddingLeft: '1.5rem' }}>
            {active.actions.map((a, i) => (
              <li key={i}>{formatAction(a)}</li>
            ))}
          </ul>
        </div>
      )}

      <h4>Players</h4>
      <table>
        <thead>
          <tr>
            <th>Seat</th>
            <th>Name</th>
            <th>Position</th>
            <th>Stack</th>
            <th>Cards</th>
            <th>Net Won</th>
          </tr>
        </thead>
        <tbody>
          {data.players.map(p => (
            <tr key={p.name}>
              <td>{p.seat}</td>
              <td>{p.name}</td>
              <td>{p.position ?? '—'}</td>
              <td>${p.stack.toFixed(2)}</td>
              <td>{p.hole_cards ?? '—'}</td>
              <td>${p.net_won.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
