import { Routes, Route, NavLink, Link } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import PlayerPage from './pages/PlayerPage.jsx'
import VideoList from './pages/VideoList.jsx'
import SceneList from './pages/SceneList.jsx'
import CharacterList from './pages/CharacterList.jsx'
import AudioTrackList from './pages/AudioTrackList.jsx'
import SubtitleList from './pages/SubtitleList.jsx'
import PlayerSettingsList from './pages/PlayerSettingsList.jsx'
import AnimationList from './pages/AnimationList.jsx'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/player', label: 'Player' },
  { to: '/video', label: 'Videos' },
  { to: '/scene', label: 'Scenes' },
  { to: '/character', label: 'Characters' },
  { to: '/audiotrack', label: 'Audio tracks' },
  { to: '/subtitle', label: 'Subtitles' },
  { to: '/playersettings', label: 'Player settings' },
  { to: '/animation', label: 'Animations' }
]

export default function App() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header-inner">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              ⚛
            </span>
            <span>Newton&apos;s Cartoon Lab</span>
          </Link>
          <nav className="main-nav">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/player" element={<PlayerPage />} />
          <Route path="/player/:videoId" element={<PlayerPage />} />
          <Route path="/video" element={<VideoList />} />
          <Route path="/scene" element={<SceneList />} />
          <Route path="/character" element={<CharacterList />} />
          <Route path="/audiotrack" element={<AudioTrackList />} />
          <Route path="/subtitle" element={<SubtitleList />} />
          <Route path="/playersettings" element={<PlayerSettingsList />} />
          <Route path="/animation" element={<AnimationList />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
      </main>

      <footer className="site-footer">
        A cartoon lesson on Newton&apos;s three laws of motion, for secondary school
        students. Volume, full screen, playback speed and language switching included.
      </footer>
    </div>
  )
}
