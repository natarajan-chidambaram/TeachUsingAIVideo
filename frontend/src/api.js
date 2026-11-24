// Thin fetch wrapper around the FastAPI backend.
// Every backend route already starts with a leading slash, so paths are
// concatenated as `${API_BASE}${path}` with exactly one slash.

const API_BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })

  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    const detail =
      payload && payload.detail
        ? typeof payload.detail === 'string'
          ? payload.detail
          : JSON.stringify(payload.detail)
        : payload && payload.message
          ? payload.message
          : `Request failed with status ${response.status}`
    const error = new Error(detail)
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload
}

export const apiGet = (path) => request(path, { method: 'GET' })

export const apiPost = (path, body) =>
  request(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

export const apiPut = (path, body) =>
  request(path, { method: 'PUT', body: JSON.stringify(body ?? {}) })

export const apiDelete = (path, body) =>
  request(path, {
    method: 'DELETE',
    body: body === undefined ? undefined : JSON.stringify(body)
  })

// ---------------------------------------------------------------------------
// Entity helpers
// ---------------------------------------------------------------------------

// The collection routes of the backend, keyed by entity name. They are all
// singular and all end with a slash.
export const ENTITIES = {
  video: {
    label: 'Video',
    list: '/video/',
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'text', required: true },
      { name: 'durationSeconds', label: 'Duration (s)', type: 'number', required: true },
      { name: 'fileUrl', label: 'File URL', type: 'text', required: true },
      { name: 'thumbnailUrl', label: 'Thumbnail URL', type: 'text', required: true },
      { name: 'learningObjectives', label: 'Learning objectives', type: 'text', required: true },
      { name: 'creationDate', label: 'Creation date', type: 'datetime-local', required: true },
      { name: 'version', label: 'Version', type: 'text', required: true },
      { name: 'subtitles', label: 'Subtitles', type: 'ref', ref: 'subtitle' },
      { name: 'audioTracks', label: 'Audio tracks', type: 'ref', ref: 'audiotrack' },
      { name: 'scenes', label: 'Scenes', type: 'ref', ref: 'scene' },
      { name: 'playerSettings', label: 'Player settings', type: 'ref', ref: 'playersettings' }
    ]
  },
  subtitle: {
    label: 'Subtitle',
    list: '/subtitle/',
    fields: [
      { name: 'languageCode', label: 'Language code', type: 'text', required: true },
      { name: 'format', label: 'Format', type: 'text', required: true },
      { name: 'fileUrl', label: 'File URL', type: 'text', required: true },
      { name: 'isEnabledByDefault', label: 'Enabled by default', type: 'boolean' },
      { name: 'subtitleVideo', label: 'Videos', type: 'ref', ref: 'video' }
    ]
  },
  scene: {
    label: 'Scene',
    list: '/scene/',
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'sequenceIndex', label: 'Sequence index', type: 'number', required: true },
      { name: 'startTimeSeconds', label: 'Start (s)', type: 'number', required: true },
      { name: 'endTimeSeconds', label: 'End (s)', type: 'number', required: true },
      { name: 'storyboardNotes', label: 'Storyboard notes', type: 'text', required: true },
      { name: 'video', label: 'Video', type: 'ref', ref: 'video', required: true },
      { name: 'scenes', label: 'Characters', type: 'ref', ref: 'character' }
    ]
  },
  playersettings: {
    label: 'Player settings',
    list: '/playersettings/',
    fields: [
      { name: 'volume', label: 'Volume', type: 'number', required: true },
      { name: 'isFullScreen', label: 'Full screen', type: 'boolean' },
      { name: 'playbackSpeed', label: 'Playback speed', type: 'number', required: true },
      { name: 'activeLanguageCode', label: 'Active language', type: 'text', required: true },
      { name: 'isMuted', label: 'Muted', type: 'boolean' },
      { name: 'currentTimeSeconds', label: 'Current time (s)', type: 'number', required: true },
      { name: 'isLooping', label: 'Looping', type: 'boolean' },
      { name: 'currentVideo', label: 'Current video', type: 'ref', ref: 'video' },
      { name: 'activeAudioTrack', label: 'Active audio track', type: 'ref', ref: 'audiotrack' },
      { name: 'activeSubtitle', label: 'Active subtitle', type: 'ref', ref: 'subtitle' }
    ]
  },
  character: {
    label: 'Character',
    list: '/character/',
    fields: [
      { name: 'name', label: 'Name', type: 'text', required: true },
      { name: 'role', label: 'Role', type: 'text', required: true },
      { name: 'avatarImageUrl', label: 'Avatar image URL', type: 'text', required: true },
      { name: 'voiceActor', label: 'Voice actor', type: 'text', required: true },
      { name: 'characters', label: 'Scenes', type: 'ref', ref: 'scene' }
    ]
  },
  audiotrack: {
    label: 'Audio track',
    list: '/audiotrack/',
    fields: [
      { name: 'languageCode', label: 'Language code', type: 'text', required: true },
      { name: 'kind', label: 'Kind', type: 'text', required: true },
      { name: 'fileUrl', label: 'File URL', type: 'text', required: true },
      { name: 'durationSeconds', label: 'Duration (s)', type: 'number', required: true },
      { name: 'volumeLevelDefault', label: 'Default volume', type: 'number', required: true },
      { name: 'isDefault', label: 'Default track', type: 'boolean' },
      { name: 'videos', label: 'Videos', type: 'ref', ref: 'video' }
    ]
  },
  animation: {
    label: 'Animation',
    list: '/animation/',
    fields: [
      { name: 'animationType', label: 'Animation type', type: 'text', required: true },
      { name: 'startTimeSeconds', label: 'Start (s)', type: 'number', required: true },
      { name: 'endTimeSeconds', label: 'End (s)', type: 'number', required: true },
      { name: 'parameters', label: 'Parameters', type: 'text', required: true },
      { name: 'targetObjectId', label: 'Target object id', type: 'text' },
      { name: 'scene', label: 'Scene', type: 'ref', ref: 'scene', required: true },
      { name: 'targetCharacter', label: 'Target character', type: 'ref', ref: 'character' }
    ]
  }
}

// Fetch a list of records for a reference dropdown.
export async function fetchOptions(entityName) {
  const entity = ENTITIES[entityName]
  if (!entity) return []
  const rows = await apiGet(entity.list)
  return Array.isArray(rows) ? rows : []
}

// The backend wraps a single record under its lowercased name for some
// entities and returns it bare for others; the player only ever needs the
// fields, so both shapes are flattened.
export function unwrap(payload, entityName) {
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    const key = entityName
    if (payload[key] && typeof payload[key] === 'object') return payload[key]
  }
  return payload
}

export { API_BASE }
