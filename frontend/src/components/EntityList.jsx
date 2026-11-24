import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost, apiPut, apiDelete, ENTITIES, fetchOptions, unwrap } from '../api.js'

/**
 * Generic CRUD screen shared by every entity.
 *
 * `entityName` selects the backend collection route and the field metadata
 * from api.js. Create posts to the collection route; Edit puts to the record
 * route; Delete removes it. Every fetch has loading, empty and error states.
 */
export default function EntityList({ entityName }) {
  const entity = ENTITIES[entityName]
  const [rows, setRows] = useState([])
  const [options, setOptions] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null) // null | 'new' | record id
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiGet(entity.list)
      setRows(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Could not load the records.')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [entity.list])

  useEffect(() => {
    load()
  }, [load])

  // Reference dropdowns are filled once per entity type.
  useEffect(() => {
    let cancelled = false
    const refs = [...new Set(entity.fields.filter((f) => f.type === 'ref').map((f) => f.ref))]
    Promise.all(refs.map(async (ref) => [ref, await fetchOptions(ref)]))
      .then((entries) => {
        if (!cancelled) setOptions(Object.fromEntries(entries))
      })
      .catch(() => {
        if (!cancelled) setOptions({})
      })
    return () => {
      cancelled = true
    }
  }, [entity.fields])

  const recordPath = useCallback(
    (id) => `${entity.list.replace(/\/$/, '')}/${id}/`,
    [entity.list]
  )

  const emptyForm = useMemo(() => {
    const base = {}
    entity.fields.forEach((field) => {
      if (field.type === 'boolean') base[field.name] = false
      else if (field.type === 'number') base[field.name] = ''
      else if (field.type === 'ref') base[field.name] = []
      else base[field.name] = ''
    })
    return base
  }, [entity.fields])

  const startCreate = () => {
    setForm(emptyForm)
    setEditing('new')
    setError('')
    setNotice('')
  }

  const startEdit = (row) => {
    const next = { ...emptyForm }
    entity.fields.forEach((field) => {
      const value = row[field.name]
      if (field.type === 'ref') {
        next[field.name] = Array.isArray(value)
          ? value.map((item) => (typeof item === 'object' ? item.id : item))
          : value === null || value === undefined
            ? []
            : [value]
      } else if (field.type === 'boolean') {
        next[field.name] = Boolean(value)
      } else {
        next[field.name] = value === null || value === undefined ? '' : value
      }
    })
    setForm(next)
    setEditing(row.id)
    setError('')
    setNotice('')
  }

  const cancelEdit = () => {
    setEditing(null)
    setForm({})
  }

  const handleChange = (field, rawValue) => {
    setForm((previous) => {
      const next = { ...previous }
      if (field.type === 'boolean') {
        next[field.name] = rawValue
      } else if (field.type === 'number') {
        next[field.name] = rawValue === '' ? '' : Number(rawValue)
      } else if (field.type === 'ref') {
        const ids = rawValue.map((option) => Number(option))
        next[field.name] = ids
      } else {
        next[field.name] = rawValue
      }
      return next
    })
  }

  // Build the request payload in the exact shape of the create schema.
  const buildPayload = () => {
    const payload = {}
    entity.fields.forEach((field) => {
      const value = form[field.name]
      if (field.type === 'boolean') {
        payload[field.name] = Boolean(value)
      } else if (field.type === 'number') {
        payload[field.name] = value === '' ? 0 : Number(value)
      } else if (field.type === 'ref') {
        const list = Array.isArray(value) ? value : value === '' ? [] : [value]
        payload[field.name] = list.map((item) => Number(item))
      } else {
        payload[field.name] = value === '' ? '' : value
      }
    })
    return payload
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = buildPayload()
      if (editing === 'new') {
        await apiPost(entity.list, payload)
        setNotice(`${entity.label} created.`)
      } else {
        await apiPut(recordPath(editing), payload)
        setNotice(`${entity.label} updated.`)
      }
      setEditing(null)
      setForm({})
      await load()
    } catch (err) {
      setError(err.message || 'The record could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (row) => {
    const name = row.title || row.name || row.languageCode || `#${row.id}`
    if (!window.confirm(`Delete this ${entity.label.toLowerCase()} (${name})?`)) return
    setError('')
    setNotice('')
    try {
      await apiDelete(recordPath(row.id))
      setNotice(`${entity.label} deleted.`)
      if (editing === row.id) cancelEdit()
      await load()
    } catch (err) {
      setError(err.message || 'The record could not be deleted.')
    }
  }

  const columns = entity.fields.slice(0, 5)

  const renderControl = (field) => {
    const value = form[field.name]
    if (field.type === 'boolean') {
      return (
        <div className="field checkbox-field" key={field.name}>
          <input
            id={`${entityName}-${field.name}`}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => handleChange(field, event.target.checked)}
          />
          <label htmlFor={`${entityName}-${field.name}`}>{field.label}</label>
        </div>
      )
    }
    if (field.type === 'ref') {
      const referenceOptions = options[field.ref] || []
      const labelOf = (option) =>
        option.title || option.name || option.languageCode || `#${option.id}`
      const selected = Array.isArray(value) ? value : []
      return (
        <div className="field" key={field.name}>
          <label htmlFor={`${entityName}-${field.name}`}>{field.label}</label>
          <select
            id={`${entityName}-${field.name}`}
            multiple
            size={Math.min(4, Math.max(2, referenceOptions.length))}
            value={selected.map(String)}
            onChange={(event) =>
              handleChange(
                field,
                Array.from(event.target.selectedOptions).map((option) => option.value)
              )
            }
          >
            {referenceOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {labelOf(option)}
              </option>
            ))}
          </select>
        </div>
      )
    }
    if (field.type === 'number') {
      return (
        <div className="field" key={field.name}>
          <label htmlFor={`${entityName}-${field.name}`}>{field.label}</label>
          <input
            id={`${entityName}-${field.name}`}
            type="number"
            step="any"
            value={value === null || value === undefined ? '' : value}
            onChange={(event) => handleChange(field, event.target.value)}
          />
        </div>
      )
    }
    if (field.type === 'datetime-local') {
      return (
        <div className="field" key={field.name}>
          <label htmlFor={`${entityName}-${field.name}`}>{field.label}</label>
          <input
            id={`${entityName}-${field.name}`}
            type="datetime-local"
            value={value === null || value === undefined ? '' : String(value).slice(0, 16)}
            onChange={(event) => handleChange(field, event.target.value)}
          />
        </div>
      )
    }
    return (
      <div className="field" key={field.name}>
        <label htmlFor={`${entityName}-${field.name}`}>{field.label}</label>
        <input
          id={`${entityName}-${field.name}`}
          type="text"
          value={value === null || value === undefined ? '' : value}
          onChange={(event) => handleChange(field, event.target.value)}
        />
      </div>
    )
  }

  const displayValue = (row, field) => {
    const value = row[field.name]
    if (field.type === 'boolean') {
      return value ? <span className="tag tag-green">Yes</span> : <span className="tag">No</span>
    }
    if (field.type === 'ref') {
      const list = Array.isArray(value) ? value : value === null || value === undefined ? [] : [value]
      if (!list.length) return <span style={{ color: '#9a93ad' }}>-</span>
      return list
        .map((item) => (typeof item === 'object' ? item.id : item))
        .join(', ')
    }
    if (value === null || value === undefined || value === '') {
      return <span style={{ color: '#9a93ad' }}>-</span>
    }
    const text = String(value)
    return text.length > 70 ? `${text.slice(0, 70)}...` : text
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{entity.label}s</h1>
          <p>Create, edit and delete the {entity.label.toLowerCase()} records of the lesson.</p>
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn-primary" onClick={startCreate}>
            + New {entity.label.toLowerCase()}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {editing !== null && (
        <div className="card">
          <h2>{editing === 'new' ? `New ${entity.label.toLowerCase()}` : `Edit ${entity.label.toLowerCase()}`}</h2>
          <p className="card-sub">
            {editing === 'new'
              ? 'Fill in the fields and save to create a new record.'
              : `Editing record #${editing}.`}
          </p>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">{entity.fields.map(renderControl)}</div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={cancelEdit} disabled={saving}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="page-head" style={{ marginBottom: 14 }}>
          <h2>All {entity.label.toLowerCase()}s</h2>
          <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="state">
            <div className="spinner" />
            <h3>Loading {entity.label.toLowerCase()}s...</h3>
          </div>
        ) : rows.length === 0 ? (
          <div className="empty-state">
            <h3>No {entity.label.toLowerCase()}s yet</h3>
            <p>Create the first one with the button above.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  {columns.map((field) => (
                    <th key={field.name}>{field.label}</th>
                  ))}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    {columns.map((field) => (
                      <td key={field.name}>{displayValue(row, field)}</td>
                    ))}
                    <td>
                      <div className="cell-actions">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => startEdit(row)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(row)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
