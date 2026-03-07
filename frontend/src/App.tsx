import { useState } from 'react'
import './App.css'
import { ImportPanel } from './components/ImportPanel'
import { StatsPanel } from './components/StatsPanel'
import { HandsTable } from './components/HandsTable'

const PLAYER = 'Hero'

function App() {
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div>
      <h1>Poker Geeks Lab</h1>

      <section>
        <h2>Import Hands</h2>
        <ImportPanel onImportComplete={() => setRefreshKey(k => k + 1)} />
      </section>

      <section key={refreshKey}>
        <h2>Stats — {PLAYER}</h2>
        <StatsPanel player={PLAYER} />
      </section>

      <section>
        <h2>Hands — {PLAYER}</h2>
        <HandsTable player={PLAYER} />
      </section>
    </div>
  )
}

export default App
