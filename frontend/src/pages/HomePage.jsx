import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../api.js'

export default function HomePage() {
  const [stats, setStats] = useState(null)
  const [video, setVideo] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([apiGet('/statistics'), apiGet('/video/')])
      .then(([statistics, videos]) => {
        if (cancelled) return
        setStats(statistics)
        const list = Array.isArray(videos) ? videos : []
        setVideo(list.length ? list[0] : null)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'The backend is not reachable.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <>
      <section className="home-hero">
        <h1>Newton&apos;s three laws, in cartoons.</h1>
        <p>
          A three minute cartoon adventure with Newton the Fox, Inky the Ball and Rocket the
          Robot. Watch inertia, F = m x a and action-reaction play out as slapstick, and
          steer the lesson with volume, full screen, playback speed and language controls.
        </p>
        <div className="btn-row">
          <Link className="btn btn-primary" to="/player">
            ▶ Play the lesson
          </Link>
          <Link className="btn btn-secondary" to="/video">
            Browse the video library
          </Link>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="feature-grid">
        <div className="feature">
          <div className="feature-icon">🔊</div>
          <h3>Volume control</h3>
          <p>Slide the volume or mute the narration; the level is stored with the player.</p>
        </div>
        <div className="feature">
          <div className="feature-icon">⛶</div>
          <h3>Full screen</h3>
          <p>One button puts the cartoon on the whole screen for class or revision.</p>
        </div>
        <div className="feature">
          <div className="feature-icon">⏩</div>
          <h3>Playback speed</h3>
          <p>Slow it down to 0.25x for a tricky formula, or speed it up to 2x for revision.</p>
        </div>
        <div className="feature">
          <div className="feature-icon">🌍</div>
          <h3>Language switching</h3>
          <p>Switch narration and subtitles between the languages the lesson was made in.</p>
        </div>
      </div>

      <div className="card">
        <h2>The lesson</h2>
        <p className="card-sub">The cartoon video this application was built to run.</p>
        {loading ? (
          <div className="state">
            <div className="spinner" />
            <h3>Loading the lesson...</h3>
          </div>
        ) : video ? (
          <div className="player-layout">
            <div>
              <div className="video-frame">
                <video
                  src={video.fileUrl}
                  poster={video.thumbnailUrl}
                  controls
                  preload="metadata"
                />
              </div>
              <div className="btn-row" style={{ marginTop: 14 }}>
                <Link className="btn btn-primary" to="/player">
                  Open the full player
                </Link>
              </div>
            </div>
            <aside>
              <div className="card" style={{ marginTop: 0 }}>
                <h3>{video.title}</h3>
                <p className="card-sub">{video.description}</p>
                <div className="lesson-meta">
                  <span className="tag tag-orange">{video.durationSeconds}s</span>
                  <span className="tag">v{video.version}</span>
                </div>
                <h3>Learning objectives</h3>
                <ul className="objectives-list">
                  {(video.learningObjectives || '')
                    .split('(1)')
                    .filter(Boolean)
                    .map((part, index) => (
                      <li key={index}>{part.replace(/^\s*\d?\)?\s*/, '').trim()}</li>
                    ))}
                </ul>
              </div>
            </aside>
          </div>
        ) : (
          <div className="empty-state">
            <h3>No video yet</h3>
            <p>Add a video record and it will show up here.</p>
          </div>
        )}
      </div>

      {stats && (
        <div className="card">
          <h2>Library at a glance</h2>
          <p className="card-sub">Everything the lesson is built from.</p>
          <div className="stat-row">
            <div className="stat">
              <div className="stat-value">{stats.video_count}</div>
              <div className="stat-label">Videos</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.scene_count}</div>
              <div className="stat-label">Scenes</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.character_count}</div>
              <div className="stat-label">Characters</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.audiotrack_count}</div>
              <div className="stat-label">Audio tracks</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.subtitle_count}</div>
              <div className="stat-label">Subtitles</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.animation_count}</div>
              <div className="stat-label">Animations</div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
