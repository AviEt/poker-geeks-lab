import { useEffect, useState } from 'react'
import { fetchHandDetail } from '../api/client'
import type { HandDetail as HandDetailType, HandAction, HandPlayer } from '../api/client'
import './HandDetail.css'

interface Props {
  player: string
  handId: string
  onClose: () => void
}

const SUIT_SYMBOL: Record<string, string> = { s: '\u2660', h: '\u2665', d: '\u2666', c: '\u2663' }

function cardDisplay(card: string) {
  const rank = card.slice(0, -1)
  const suitChar = card.slice(-1)
  const symbol = SUIT_SYMBOL[suitChar] ?? suitChar
  const isRed = suitChar === 'h' || suitChar === 'd'
  return { rank, symbol, isRed, text: `${rank}${symbol}` }
}

function parseCards(cardsStr: string | null): string[] {
  if (!cardsStr) return []
  return cardsStr.trim().split(/\s+/)
}

function BoardCards({ streets }: { streets: HandDetailType['streets'] }) {
  const allCards: { card: string; revealed: boolean }[] = []
  for (const s of streets) {
    for (const c of parseCards(s.cards)) {
      allCards.push({ card: c, revealed: true })
    }
  }
  while (allCards.length < 5) {
    allCards.push({ card: '', revealed: false })
  }

  return (
    <div className="hand-detail__board">
      {allCards.map((c, i) => {
        if (!c.revealed) {
          return <div key={i} className="board-card board-card--unrevealed" />
        }
        const d = cardDisplay(c.card)
        return (
          <div
            key={i}
            className={`board-card ${d.isRed ? 'board-card--heart' : 'board-card--spade'}`}
          >
            {d.text}
          </div>
        )
      })}
    </div>
  )
}

function CardPair({ cards, hidden = false }: { cards: string[]; hidden?: boolean }) {
  const display = cards.length > 0 ? cards : ['', '']
  return (
    <div className="card-pair">
      {display.map((c, i) => {
        if (hidden || !c) return <div key={i} className="card-sm card-sm--hidden" />
        const d = cardDisplay(c)
        return (
          <div key={i} className={`card-sm ${d.isRed ? 'card-sm--red' : 'card-sm--black'}`}>
            {d.text}
          </div>
        )
      })}
    </div>
  )
}

function PlayerChip({ p, isHero }: { p: HandPlayer; isHero: boolean }) {
  const initials = p.name.slice(0, 2).toUpperCase()
  const cards = parseCards(p.hole_cards)
  const hasCards = cards.length > 0
  const resultClass = p.net_won > 0.001
    ? 'player-chip__result--positive'
    : p.net_won < -0.001
      ? 'player-chip__result--negative'
      : 'player-chip__result--neutral'

  return (
    <div className="player-chip">
      <div className={`player-chip__avatar ${isHero ? 'player-chip__avatar--hero' : ''}`}>
        {initials}
      </div>
      <span className="player-chip__name">{p.name}</span>
      <span className="player-chip__position">{p.position ?? ''}</span>
      <span className="player-chip__stack">${p.stack.toFixed(2)}</span>
      <CardPair cards={cards} hidden={!hasCards} />
      <span className={`player-chip__result ${resultClass}`}>
        {p.net_won >= 0 ? '+' : ''}{p.net_won.toFixed(2)}
      </span>
    </div>
  )
}

function formatAction(a: HandAction): string {
  const label = a.action.replace(/_/g, ' ')
  let text = `${a.player} ${label}`
  if (a.amount != null) text += ` $${a.amount.toFixed(2)}`
  if (a.is_all_in) text += ' (all-in)'
  return text
}

function actionBadgeLabel(action: string): string {
  const labels: Record<string, string> = {
    fold: 'Fold',
    check: 'Check',
    call: 'Call',
    bet: 'Bet',
    raise: 'Raise',
    post_sb: 'SB',
    post_bb: 'BB',
    post_ante: 'Ante',
    shows: 'Shows',
    mucks: 'Mucks',
  }
  return labels[action] ?? action
}

function ActionItem({ a, heroName }: { a: HandAction; heroName: string | null }) {
  const isHero = a.player === heroName
  const initials = a.player.slice(0, 2).toUpperCase()
  const badgeClass = a.is_all_in ? 'action-item__badge--allin' : `action-item__badge--${a.action}`

  return (
    <li className="action-item">
      <div className={`action-item__avatar ${isHero ? 'action-item__avatar--hero' : ''}`}>
        {initials}
      </div>
      <div className="action-item__body">
        <div>
          <div className="action-item__player">{a.player}</div>
          <div className="action-item__text">{formatAction(a)}</div>
        </div>
        <div className="action-item__right">
          <span className={`action-item__badge ${badgeClass}`}>
            {a.is_all_in ? 'All-In' : actionBadgeLabel(a.action)}
          </span>
          {a.amount != null && (
            <span className="action-item__amount">${a.amount.toFixed(2)}</span>
          )}
        </div>
      </div>
    </li>
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

  if (!data) return <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Loading…</p>

  const active = data.streets.find(s => s.name === activeStreet)
  const showdownPlayers = data.players.filter(p => p.hole_cards && p.hole_cards.trim().length > 0)

  return (
    <div className="hand-detail" data-testid="hand-detail">
      {/* Header */}
      <div className="hand-detail__header">
        <h3 className="hand-detail__title">{data.table_name} | #{data.hand_id}</h3>
        <button className="hand-detail__close" onClick={onClose} aria-label="Close">✕</button>
      </div>
      <p className="hand-detail__subtitle">
        ${data.small_blind}/${data.big_blind} &mdash; {data.game_type}
      </p>

      {/* Players strip */}
      <div className="hand-detail__players-strip">
        {data.players.map(p => (
          <PlayerChip key={p.name} p={p} isHero={p.name === data.hero_name} />
        ))}
      </div>

      {/* Board */}
      <BoardCards streets={data.streets} />

      {/* Pot */}
      <div className="hand-detail__pot">
        Pot: ${data.pot.toFixed(2)}
      </div>

      {/* Street tabs */}
      <div className="street-tabs">
        {data.streets.map(s => (
          <button
            key={s.name}
            onClick={() => setActiveStreet(s.name)}
            className={`street-tab ${activeStreet === s.name ? 'street-tab--active' : ''}`}
            data-testid={`tab-${s.name}`}
          >
            <span className="street-tab__label">
              {s.name.charAt(0).toUpperCase() + s.name.slice(1)}
            </span>
            {s.cards && (
              <span className="street-tab__cards">{s.cards}</span>
            )}
          </button>
        ))}
      </div>

      {/* Action timeline */}
      {active && (
        <ul className="action-timeline" data-testid="street-actions">
          {active.actions.map((a, i) => (
            <ActionItem key={i} a={a} heroName={data.hero_name} />
          ))}
        </ul>
      )}

      {/* Showdown */}
      {showdownPlayers.length > 1 && (
        <div className="hand-detail__showdown" data-testid="showdown">
          <div className="hand-detail__showdown-title">Showdown</div>
          <div className="showdown-players">
            {showdownPlayers.map(p => {
              const cards = parseCards(p.hole_cards)
              const resultClass = p.net_won > 0.001
                ? 'showdown-player__result--positive'
                : 'showdown-player__result--negative'
              return (
                <div key={p.name} className="showdown-player">
                  <CardPair cards={cards} />
                  <div className="showdown-player__info">
                    <span className="showdown-player__name">{p.name}</span>
                    <span className={`showdown-player__result ${resultClass}`}>
                      {p.net_won >= 0 ? '+' : ''}{p.net_won.toFixed(2)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
