import { useEffect, useState } from 'react'
import { fetchStats } from '../api/client'
import type { PlayerStats } from '../api/client'

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

  if (loading) return <div data-testid="loading">Loading stats…</div>
  if (!stats) return null

  return (
    <div>
      <span data-testid="hands">{stats.hands}</span> hands
      <table>
        <tbody>
          <tr>
            <td>VPIP</td>
            <td data-testid="vpip">{stats.vpip}</td>
          </tr>
          <tr>
            <td>PFR</td>
            <td data-testid="pfr">{stats.pfr}</td>
          </tr>
          <tr>
            <td>BB/100</td>
            <td data-testid="bb100">{stats.bb_per_100.toFixed(2)}</td>
          </tr>
          <tr>
            <td>BB/100 adj</td>
            <td data-testid="bb100adj">{stats.bb_per_100_adjusted.toFixed(2)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
