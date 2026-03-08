import './CardChips.css'

const SUIT_MAP: Record<string, { symbol: string; cls: string }> = {
  s: { symbol: '♠', cls: 'suit--spade' },
  h: { symbol: '♥', cls: 'suit--heart' },
  d: { symbol: '♦', cls: 'suit--diamond' },
  c: { symbol: '♣', cls: 'suit--club' },
}

interface Props {
  cards: string | null | undefined
}

export function CardChips({ cards }: Props) {
  if (!cards) return <span className="card-chips--empty">—</span>

  const parts = cards.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return <span className="card-chips--empty">—</span>

  return (
    <span className="card-chips">
      {parts.map((card, i) => {
        const rank = card.slice(0, -1)
        const suitChar = card.slice(-1).toLowerCase()
        const suit = SUIT_MAP[suitChar]
        if (!suit) return <span key={i} className="card-chip">{card}</span>
        return (
          <span key={i} className={`card-chip ${suit.cls}`}>
            {rank}{suit.symbol}
          </span>
        )
      })}
    </span>
  )
}
