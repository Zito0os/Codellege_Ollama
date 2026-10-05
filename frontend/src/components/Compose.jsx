import { useState } from 'react'
import { CUISINE_OPTIONS, UNITS } from '../data/options'
import { normalizeKey } from '../utils/normalize'

function makeId() {
  return `ing-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
}

function normalizeItem(item) {
  if (item.qty != null && item.unit) return item
  const match = String(item.amount || '').match(/^(\d+(?:[.,]\d+)?)\s*(.*)$/)
  return {
    ...item,
    qty: match ? match[1].replace(',', '.') : '1',
    unit: match?.[2]?.trim() || 'piezas',
  }
}

function titleCase(value) {
  const t = value.trim()
  if (!t) return t
  return t.charAt(0).toUpperCase() + t.slice(1)
}

function unitLabel(id) {
  return UNITS.find((u) => u.id === id)?.label || id
}

function IconPencil() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 20h4.5L19 9.5 14.5 5 4 15.5V20z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M13.2 6.3l4.5 4.5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  )
}

function IconClose() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export default function Compose({
  tools,
  ingredients,
  onIngredientsChange,
  onGenerate,
  onEditTools,
  onOpenHistory,
  generating,
}) {
  const list = ingredients.map(normalizeItem)
  const [name, setName] = useState('')
  const [qty, setQty] = useState('1')
  const [unit, setUnit] = useState('piezas')
  const [types, setTypes] = useState([])
  const [note, setNote] = useState('')
  const [ingError, setIngError] = useState('')
  const [editingId, setEditingId] = useState(null)

  function persist(next) {
    onIngredientsChange(next.map(normalizeItem))
  }

  function addIngredient(e) {
    e.preventDefault()
    const n = name.trim()
    const q = String(qty).trim()
    if (!n || !q) {
      setIngError('Nombre y cantidad obligatorios.')
      return
    }
    if (Number(q) <= 0) {
      setIngError('La cantidad debe ser mayor a 0.')
      return
    }
    const key = normalizeKey(n)
    if (list.some((item) => normalizeKey(item.name) === key)) {
      setIngError(`“${n}” ya está en la lista.`)
      return
    }
    // Aviso suave de parecidos; la IA filtrará mejor después.
    const similar = list.find((item) => {
      const a = normalizeKey(item.name)
      return a.includes(key) || key.includes(a)
    })
    if (similar) {
      setIngError(`Parece similar a “${similar.name}”. Usa el lápiz para editar ese.`)
      return
    }
    setIngError('')
    persist([
      ...list,
      {
        id: makeId(),
        name: titleCase(n),
        qty: q,
        unit,
        amount: `${q} ${unit}`,
      },
    ])
    setName('')
    setQty('1')
  }

  function removeIngredient(id) {
    if (editingId === id) setEditingId(null)
    persist(list.filter((i) => i.id !== id))
  }

  function updateQty(id, nextQty) {
    const cleaned = String(nextQty).replace(/[^\d.,]/g, '')
    persist(
      list.map((item) =>
        item.id === id
          ? { ...item, qty: cleaned, amount: `${cleaned} ${item.unit}` }
          : item,
      ),
    )
  }

  function bumpQty(id, delta) {
    const item = list.find((i) => i.id === id)
    if (!item) return
    const current = parseFloat(String(item.qty).replace(',', '.')) || 0
    const step = item.unit === 'kg' || item.unit === 'L' ? 0.1 : 1
    const next = Math.max(step, Math.round((current + delta * step) * 10) / 10)
    updateQty(id, String(next))
  }

  function updateUnit(id, nextUnit) {
    persist(
      list.map((item) =>
        item.id === id
          ? { ...item, unit: nextUnit, amount: `${item.qty} ${nextUnit}` }
          : item,
      ),
    )
  }

  function onChipClose(id) {
    if (editingId === id) {
      setEditingId(null)
      return
    }
    removeIngredient(id)
  }

  function toggleType(label) {
    if (types.includes(label)) {
      setTypes(types.filter((t) => t !== label))
      return
    }
    if (types.length >= 4) return
    setTypes([...types, label])
  }

  function submit() {
    if (!list.length) {
      setIngError('Agrega al menos un ingrediente.')
      return
    }
    onGenerate({
      types: types.length ? types : ['Rápida'],
      note,
    })
  }

  return (
    <section className="compose compose--fit">
      <header className="compose__head">
        <div>
          <h1 className="display display--md">Tu refrigerador</h1>
          <p className="muted compose__sub">
            {tools.slice(0, 3).join(' · ')}
            {tools.length > 3 ? ` · +${tools.length - 3}` : ''}
          </p>
        </div>
        <div className="compose__actions">
          <button type="button" className="btn btn--soft" onClick={onEditTools}>
            Herramientas
          </button>
          <button type="button" className="btn btn--soft" onClick={onOpenHistory}>
            Historial
          </button>
        </div>
      </header>

      <div className="compose__split">
        <article className="panel panel--lite">
          <h2>Ingredientes</h2>

          <form className="row-form row-form--ings" onSubmit={addIngredient}>
            <label className="field field--name">
              <span>Qué tienes</span>
              <input
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  setIngError('')
                }}
                placeholder="Jamón"
              />
            </label>
            <label className="field field--qty">
              <span>Cant.</span>
              <input
                inputMode="decimal"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                placeholder="1"
              />
            </label>
            <label className="field field--unit">
              <span>Unidad</span>
              <select value={unit} onChange={(e) => setUnit(e.target.value)}>
                {UNITS.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.label}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="btn btn--soft btn--solid btn--add" aria-label="Añadir">
              +
            </button>
          </form>
          {ingError ? <p className="field__error">{ingError}</p> : null}

          <ul className="ing-list">
            {list.map((item) => {
              const editing = editingId === item.id
              return (
                <li key={item.id} className={`ing-chip ${editing ? 'ing-chip--editing' : ''}`}>
                  <strong className="ing-chip__name">{item.name}</strong>
                  {!editing && (
                    <span className="ing-chip__meta">
                      {item.qty} {unitLabel(item.unit)}
                    </span>
                  )}
                  {editing && (
                    <>
                      <div className="qty-control">
                        <button type="button" aria-label="Menos" onClick={() => bumpQty(item.id, -1)}>
                          −
                        </button>
                        <input
                          inputMode="decimal"
                          value={item.qty}
                          onChange={(e) => updateQty(item.id, e.target.value)}
                          aria-label={`Cantidad de ${item.name}`}
                        />
                        <button type="button" aria-label="Más" onClick={() => bumpQty(item.id, 1)}>
                          +
                        </button>
                      </div>
                      <select
                        className="ing-chip__unit"
                        value={item.unit}
                        onChange={(e) => updateUnit(item.id, e.target.value)}
                        aria-label={`Unidad de ${item.name}`}
                      >
                        {UNITS.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.label}
                          </option>
                        ))}
                      </select>
                    </>
                  )}
                  {!editing && (
                    <button
                      type="button"
                      className="ing-chip__icon"
                      aria-label={`Editar ${item.name}`}
                      onClick={() => setEditingId(item.id)}
                    >
                      <IconPencil />
                    </button>
                  )}
                  <button
                    type="button"
                    className="ing-chip__icon"
                    aria-label={editing ? `Guardar ${item.name}` : `Quitar ${item.name}`}
                    onClick={() => onChipClose(item.id)}
                  >
                    <IconClose />
                  </button>
                </li>
              )
            })}
            {!list.length && <li className="empty">Agrega lo que hay en el refri.</li>}
          </ul>
        </article>

        <article className="panel panel--lite">
          <div className="panel__title-row">
            <h2>Antojo</h2>
            <span className="muted">{types.length}/4</span>
          </div>

          <div className="craving-grid" role="group" aria-label="Tipos de comida">
            {CUISINE_OPTIONS.map((label) => {
              const on = types.includes(label)
              const lockedOut = !on && types.length >= 4
              return (
                <button
                  key={label}
                  type="button"
                  className={`craving ${on ? 'craving--on' : ''}`}
                  aria-pressed={on}
                  disabled={lockedOut}
                  onClick={() => toggleType(label)}
                >
                  {label}
                </button>
              )
            })}
          </div>

          <label className="field field--note">
            <span>Nota libre</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Algo caliente, poca vajilla…"
            />
          </label>
        </article>
      </div>

      <div className="compose__cta">
        <div className="compose__cta-blur" aria-hidden="true" />
        <div className="compose__cta-inner compose__cta-inner--compact">
          <button
            type="button"
            className="btn btn--primary btn--generate"
            onClick={submit}
            disabled={!list.length || generating}
            aria-busy={generating}
          >
            {generating ? '…' : 'Generar'}
          </button>
        </div>
      </div>
    </section>
  )
}
