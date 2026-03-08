import { useEffect, useState } from 'react'
import { fetchStats } from '../api/client'
import type { PlayerStats } from '../api/client'
import './StatsPanel.css'

interface Props {
  player: string
}

export function StatsPanel({ player }: Props) {
  const [stats, setStats] = useState<PlayerStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchStats(player).then(s => {
      setStats(s)
      setLoading(false)
    })
  }, [player])

  if (loading) {
    return (
      <div data-testid="loading">
        <div className="stats-loading">
          {[0, 1, 2, 3].map(i => <div key={i} className="stats-skeleton" />)}
        </div>
      </div>
    )
  }

  if (!stats) return null

  const bb100Sign = stats.bb_per_100 >= 0 ? '+' : ''
  const bb100adjSign = stats.bb_per_100_adjusted >= 0 ? '+' : ''
  const bb100Class = stats.bb_per_100 > 0 ? 'stat-card__value--profit'
    : stats.bb_per_100 < 0 ? 'stat-card__value--loss' : ''
  const bb100adjClass = stats.bb_per_100_adjusted > 0 ? 'stat-card__value--profit'
    : stats.bb_per_100_adjusted < 0 ? 'stat-card__value--loss' : ''

  return (
    <div>
      <div className="stats-hands-count">
        <span className="stats-hands-count__num" data-testid="hands">{stats.hands.toLocaleString()}</span>
        <span>hands played</span>
      </div>

      <div className="stats-panel">
        <div className="stat-card">
          <div className="stat-card__value" data-testid="vpip">{stats.vpip}%</div>
          <div className="stat-card__label">VPIP</div>
          <div className="stat-card__sub">Vol. put $ in pot</div>
        </div>

        <div className="stat-card">
          <div className="stat-card__value" data-testid="pfr">{stats.pfr}%</div>
          <div className="stat-card__label">PFR</div>
          <div className="stat-card__sub">Preflop raise</div>
        </div>

        <div className="stat-card">
          <div className={`stat-card__value ${bb100Class}`} data-testid="bb100">
            {bb100Sign}{stats.bb_per_100.toFixed(2)}
          </div>
          <div className="stat-card__label">BB / 100</div>
          <div className="stat-card__sub">Big blinds per 100</div>
        </div>

        <div className="stat-card">
          <div className={`stat-card__value ${bb100adjClass}`} data-testid="bb100adj">
            {bb100adjSign}{stats.bb_per_100_adjusted.toFixed(2)}
          </div>
          <div className="stat-card__label">BB / 100 Adj</div>
          <div className="stat-card__sub">All-in adjusted</div>
        </div>
      </div>
    </div>
  )
}
