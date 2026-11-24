import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiGet, apiPost, unwrap } from '../api.js'

const SPEED_OPTIONS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2]

const LANGUAGE_LABELS = {
  en: 'English',
  es: 'Espanol',
  fr: 'Francais',
  de: 'Deutsch',
  it: 'Italiano',
  pt: 'Portugues',
  ar: 'Arabic',
  zh: 'Chinese'
}

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

export default function PlayerPage() {
  const navigate = useNavigate()
  const { videoId } = useParams()
  const videoRef = useRef(null)
  const frameRef = useRef(null)

  const [videos, setVideos] = useState([])
  const [video, setVideo] = useState(null)
  const [scenes, setScenes] = useState([])
  const [characters, setCharacters] = useState([])
  const [languages, setLanguages] = useState([])
  const [settings, setSettings] = useState(null)
  const [settingsId, setSettingsId] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [volume, setVolume] = useState(0.8)
  const [muted, setMuted] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const [languageCode, setLanguageCode] = useState('en')
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playing, setPlaying] = useState(false)

  // ------------------------------------------------------------ data loading

  const loadLesson = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const videoRows = await apiGet('/video/')
      const list = Array.isArray(videoRows) ? videoRows : []
      setVideos(list)
      if (!list.length) {
        setVideo(null)
        setLoading(false)
        return
      }
      const wanted = videoId ? Number(videoId) : list[0].id
      const chosen = list.find((item) => item.id === wanted) || list[0]
      setVideo(chosen)

      const [sceneRows, characterRows] = await Promise.all([
        apiGet('/scene/'),
        apiGet('/character/')
      ])
      setScenes(
        (Array.isArray(sceneRows) ? sceneRows : []).filter(
          (scene) => scene.video_id === chosen.id
        )
      )
      setCharacters(Array.isArray(characterRows) ? characterRows : [])

      // The player settings row that drives this player.
      const settingsRows = await apiGet('/playersettings/')
      const settingsList = Array.isArray(settingsRows) ? settingsRows : []
      const active =
        settingsList.find((item) => item.currentVideo_id === chosen.id) || settingsList[0] || null
      if (active) {
        setSettings(active)
        setSettingsId(active.id)
        setVolume(active.volume ?? 0.8)
        setMuted(Boolean(active.isMuted))
        setSpeed(active.playbackSpeed ?? 1)
        setIsFullScreen(Boolean(active.isFullScreen))
        setLanguageCode(active.activeLanguageCode || 'en')
        setCurrentTime(active.currentTimeSeconds || 0)
      }

      // The languages this video is available in.
      const languagePayload = await apiGet(`/video/${chosen.id}/languages/`)
      setLanguages(languagePayload.languages || [])
      setLoading(false)
    } catch (err) {
      setError(err.message || 'The lesson could not be loaded.')
      setLoading(false)
    }
  }, [videoId])

  useEffect(() => {
    loadLesson()
  }, [loadLesson])

  // ------------------------------------------------- player element wiring

  // Apply the persisted settings to the media element whenever they change.
  useEffect(() => {
    const element = videoRef.current
    if (!element) return
    element.volume = volume
    element.muted = muted
    element.playbackRate = speed
  }, [volume, muted, speed])

  // Swap the audio source and the subtitle track when the language changes.
  const activeLanguage = useMemo(
    () => languages.find((item) => item.languageCode === languageCode) || null,
    [languages, languageCode]
  )

  const audioTrack = useMemo(() => {
    if (!activeLanguage || !activeLanguage.audioTracks.length) return null
    return (
      activeLanguage.audioTracks.find((track) => track.isDefault) ||
      activeLanguage.audioTracks[0]
    )
  }, [activeLanguage])

  const subtitleTrack = useMemo(() => {
    if (!activeLanguage || !activeLanguage.subtitles.length) return null
    return (
      activeLanguage.subtitles.find((track) => track.isEnabledByDefault) ||
      activeLanguage.subtitles[0]
    )
  }, [activeLanguage])

  // ------------------------------------------------------- backend actions

  const callAction = useCallback(
    async (action, body = {}) => {
      if (!settingsId) {
        setError('No player settings are available for this lesson yet.')
        return null
      }
      try {
        const payload = await apiPost(
          `/playersettings/${settingsId}/methods/${action}/`,
          body
        )
        const updated = payload?.playersettings || null
        if (updated) {
          setSettings(updated)
          setVolume(updated.volume ?? 0.8)
          setMuted(Boolean(updated.isMuted))
          setSpeed(updated.playbackSpeed ?? 1)
          setIsFullScreen(Boolean(updated.isFullScreen))
          setLanguageCode(updated.activeLanguageCode || languageCode)
          setCurrentTime(updated.currentTimeSeconds || 0)
        }
        setError('')
        return payload
      } catch (err) {
        setError(err.message || `The ${action} action failed.`)
        return null
      }
    },
    [settingsId, languageCode]
  )

  // ---------------------------------------------------------------- actions

  const handlePlay = async () => {
    const element = videoRef.current
    if (element) {
      try {
        await element.play()
        setPlaying(true)
      } catch {
        setNotice('The browser blocked autoplay. Press play again to start the lesson.')
      }
    }
    await callAction('play')
  }

  const handlePause = async () => {
    const element = videoRef.current
    if (element) element.pause()
    setPlaying(false)
    await callAction('pause')
  }

  const handleStop = async () => {
    const element = videoRef.current
    if (element) {
      element.pause()
      element.currentTime = 0
    }
    setPlaying(false)
    setCurrentTime(0)
    await callAction('stop')
  }

  const handleSeek = async (seconds) => {
    const element = videoRef.current
    const target = Math.max(0, Math.floor(seconds))
    if (element) element.currentTime = target
    setCurrentTime(target)
    await callAction('seek', { timeSeconds: target })
  }

  const handleVolume = async (value) => {
    const level = Math.min(1, Math.max(0, Number(value)))
    setVolume(level)
    setMuted(level === 0)
    await callAction('setVolume', { level })
  }

  const handleMute = async () => {
    const next = !muted
    setMuted(next)
    await callAction('setVolume', { level: next ? 0 : volume })
  }

  const handleSpeed = async (value) => {
    const next = Number(value)
    setSpeed(next)
    await callAction('setPlaybackSpeed', { speed: next })
  }

  const handleToggleFullScreen = async () => {
    const element = frameRef.current
    try {
      if (!document.fullscreenElement) {
        if (element?.requestFullscreen) await element.requestFullscreen()
      } else if (document.exitFullscreen) {
        await document.exitFullscreen()
      }
    } catch {
      setNotice('This browser refused the full screen request.')
    }
    // The server keeps the preference; the browser keeps the actual window.
    const payload = await callAction('toggleFullScreen')
    if (payload && typeof payload.isFullScreen === 'boolean') {
      setIsFullScreen(payload.isFullScreen)
    }
  }

  const handleLanguage = async (code) => {
    const payload = await callAction('changeLanguage', { languageCode: code })
    if (payload) {
      setLanguageCode(code)
      setNotice(`Language switched to ${LANGUAGE_LABELS[code] || code}.`)
    }
  }

  const handleLoadVideo = async (id) => {
    const payload = await callAction('loadVideo', { videoId: Number(id) })
    if (payload) {
      navigate(`/player/${id}`)
      setNotice('Video loaded.')
      await loadLesson()
    }
  }

  // Keep the browser's full screen state in sync with the stored preference.
  useEffect(() => {
    const onChange = () => {
      setIsFullScreen(Boolean(document.fullscreenElement))
    }
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  // ------------------------------------------------------------- rendering

  if (loading) {
    return (
      <div className="state">
        <div className="spinner" />
        <h3>Loading the lesson...</h3>
      </div>
    )
  }

  if (!video) {
    return (
      <div className="card">
        <div className="empty-state">
          <h3>No video in the library yet</h3>
          <p>Create a video record to make it playable here.</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="lesson-title">{video.title}</h1>
          <p>Watch the cartoon lesson and control how it plays.</p>
        </div>
        {videos.length > 1 && (
          <div className="btn-row">
            <label className="control-label" htmlFor="video-picker">
              Video
            </label>
            <select
              id="video-picker"
              className="control-select"
              value={video.id}
              onChange={(event) => handleLoadVideo(event.target.value)}
            >
              {videos.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      <div className="player-layout">
        <div>
          <div className={`video-frame${isFullScreen ? ' fullscreen' : ''}`} ref={frameRef}>
            <video
              ref={videoRef}
              src={video.fileUrl}
              poster={video.thumbnailUrl}
              controls
              preload="metadata"
              onTimeUpdate={(event) => setCurrentTime(event.target.currentTime)}
              onLoadedMetadata={(event) => setDuration(event.target.duration || video.durationSeconds)}
              onEnded={() => setPlaying(false)}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
            >
              {subtitleTrack && (
                <track
                  key={subtitleTrack.id}
                  kind="subtitles"
                  src={subtitleTrack.fileUrl}
                  srcLang={subtitleTrack.languageCode}
                  label={LANGUAGE_LABELS[subtitleTrack.languageCode] || subtitleTrack.languageCode}
                  default
                />
              )}
            </video>
          </div>

          <div className="player-controls">
            <div className="control-row">
              <span className="control-label">Playback</span>
              <button type="button" className="btn btn-primary" onClick={handlePlay}>
                Play
              </button>
              <button type="button" className="btn btn-secondary" onClick={handlePause}>
                Pause
              </button>
              <button type="button" className="btn btn-secondary" onClick={handleStop}>
                Stop
              </button>
              <span className="state-pill">{playing ? 'Playing' : 'Paused'}</span>
            </div>

            <div className="control-row">
              <span className="control-label">Seek</span>
              <input
                className="progress-range"
                type="range"
                min="0"
                max={duration || video.durationSeconds || 180}
                step="1"
                value={Math.min(currentTime, duration || video.durationSeconds || 180)}
                onChange={(event) => handleSeek(event.target.value)}
                aria-label="Seek position"
              />
              <span className="time-readout">
                {formatTime(currentTime)} / {formatTime(duration || video.durationSeconds)}
              </span>
            </div>

            <div className="control-row">
              <span className="control-label">Volume</span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleMute}>
                {muted ? 'Unmute' : 'Mute'}
              </button>
              <input
                className="volume-range"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={muted ? 0 : volume}
                onChange={(event) => handleVolume(event.target.value)}
                aria-label="Volume level"
              />
              <span className="time-readout">{Math.round((muted ? 0 : volume) * 100)}%</span>
            </div>

            <div className="control-row">
              <span className="control-label">Full screen</span>
              <button type="button" className="btn btn-secondary" onClick={handleToggleFullScreen}>
                {isFullScreen ? 'Exit full screen' : 'Full screen'}
              </button>
              <span className="state-pill">{isFullScreen ? 'Full screen on' : 'Windowed'}</span>
            </div>

            <div className="control-row">
              <span className="control-label">Speed</span>
              <select
                className="control-select"
                value={speed}
                onChange={(event) => handleSpeed(event.target.value)}
                aria-label="Playback speed"
              >
                {SPEED_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}x
                  </option>
                ))}
              </select>
              <span className="state-pill">{speed}x</span>
            </div>

            <div className="control-row">
              <span className="control-label">Language</span>
              <select
                className="control-select"
                value={languageCode}
                onChange={(event) => handleLanguage(event.target.value)}
                aria-label="Video language"
              >
                {languages.length === 0 && <option value={languageCode}>{languageCode}</option>}
                {languages.map((item) => (
                  <option key={item.languageCode} value={item.languageCode}>
                    {LANGUAGE_LABELS[item.languageCode] || item.languageCode}
                  </option>
                ))}
              </select>
              {audioTrack && <span className="state-pill">Audio: {audioTrack.languageCode}</span>}
              {subtitleTrack && <span className="state-pill">Subtitles: {subtitleTrack.languageCode}</span>}
            </div>
          </div>
        </div>

        <aside>
          <div className="card">
            <h2>About this lesson</h2>
            <p className="card-sub">{video.description}</p>
            <h3>Learning objectives</h3>
            <ul className="objectives-list">
              {(video.learningObjectives || '')
                .split('(1)')
                .filter(Boolean)
                .map((part, index) => (
                  <li key={index}>{part.replace(/^\s*\d?\)?\s*/, '').trim()}</li>
                ))}
            </ul>
            <div className="lesson-meta">
              <span className="tag tag-orange">{video.durationSeconds}s</span>
              <span className="tag">v{video.version}</span>
              <span className="tag tag-green">{languageCode.toUpperCase()}</span>
            </div>
          </div>

          <div className="card">
            <h3>Scenes</h3>
            <p className="card-sub">The three laws, scene by scene.</p>
            {scenes.length === 0 ? (
              <p className="card-sub">No scenes for this video yet.</p>
            ) : (
              scenes
                .slice()
                .sort((a, b) => a.sequenceIndex - b.sequenceIndex)
                .map((scene) => (
                  <div className="scene-item" key={scene.id}>
                    <div className="scene-time">
                      {formatTime(scene.startTimeSeconds)} - {formatTime(scene.endTimeSeconds)}
                    </div>
                    <h4>{scene.title}</h4>
                    <p>{scene.storyboardNotes}</p>
                  </div>
                ))
            )}
          </div>

          <div className="card">
            <h3>Cast</h3>
            <p className="card-sub">The cartoon characters in this lesson.</p>
            <div className="character-strip">
              {characters.map((character) => (
                <div className="character-card" key={character.id}>
                  <img src={character.avatarImageUrl} alt={character.name} />
                  <div>
                    <strong>{character.name}</strong>
                    <span>{character.role}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}
