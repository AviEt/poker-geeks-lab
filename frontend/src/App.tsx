import { useState } from 'react'
import './App.css'
import { ImportPanel } from './components/ImportPanel'
import { StatsPanel } from './components/StatsPanel'
import { HandsTable } from './components/HandsTable'
import { HandDetail } from './components/HandDetail'

const PLAYER = 'Hero'

type Section = 'import' | 'stats' | 'hands'

const NAV_ITEMS: { id: Section; icon: string; label: string }[] = [
  { id: 'import', icon: '⬆', label: 'Import' },
  { id: 'stats',  icon: '📊', label: 'Stats' },
  { id: 'hands',  icon: '🃏', label: 'Hands' },
]

function App() {
  const [section, setSection] = useState<Section>('stats')
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedHandId, setSelectedHandId] = useState<string | null>(null)

  const handleImportComplete = () => {
    setRefreshKey(k => k + 1)
    setSection('stats')
  }

  const handleSelectHand = (handId: string) => {
    setSelectedHandId(handId)
  }

  const handleCloseHand = () => {
    setSelectedHandId(null)
  }

  return (
    <div className="app-shell">
      {/* ── Sidebar (desktop) ── */}
      <aside className="app-sidebar">
        <div className="app-sidebar__logo">
          <div className="app-sidebar__logo-icon">♠</div>
          <div>
            <div className="app-sidebar__logo-text">Poker Geeks Lab</div>
            <div className="app-sidebar__logo-sub">Analytics</div>
          </div>
        </div>
        <nav className="app-sidebar__nav">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              className={`nav-link ${section === item.id ? 'nav-link--active' : ''}`}
              onClick={() => { setSection(item.id); setSelectedHandId(null) }}
            >
              <span className="nav-link__icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* ── Main content ── */}
      <div className="app-main">
        {/* Mobile header */}
        <header className="app-mobile-header">
          <div className="app-mobile-header__logo">
            <div className="app-mobile-header__icon">♠</div>
            <span className="app-mobile-header__title">Poker Geeks Lab</span>
          </div>
        </header>

        {/* Page content */}
        <main className="app-page">
          {section === 'import' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Import Hands</h1>
                <p className="page-subtitle">Upload PokerStars hand history .txt files</p>
              </div>
              <ImportPanel onImportComplete={handleImportComplete} />
            </>
          )}

          {section === 'stats' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Stats — {PLAYER}</h1>
                <p className="page-subtitle">Lifetime performance metrics</p>
              </div>
              <StatsPanel key={refreshKey} player={PLAYER} />
            </>
          )}

          {section === 'hands' && (
            <>
              {selectedHandId ? (
                <HandDetail
                  player={PLAYER}
                  handId={selectedHandId}
                  onClose={handleCloseHand}
                />
              ) : (
                <>
                  <div className="page-header">
                    <h1 className="page-title">Hands — {PLAYER}</h1>
                    <p className="page-subtitle">Click a row to view hand detail</p>
                  </div>
                  <HandsTable player={PLAYER} onSelectHand={handleSelectHand} />
                </>
              )}
            </>
          )}
        </main>

        {/* Mobile bottom nav */}
        <nav className="app-bottom-nav">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              className={`bottom-tab ${section === item.id ? 'bottom-tab--active' : ''}`}
              onClick={() => { setSection(item.id); setSelectedHandId(null) }}
            >
              <span className="bottom-tab__icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  )
}

export default App
