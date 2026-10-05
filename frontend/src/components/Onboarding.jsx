import { useMemo, useState } from 'react'
import { DEFAULT_TOOLS } from '../data/tools'

export default function Onboarding({ onComplete, initialTools = [] }) {
  const tools = useMemo(() => DEFAULT_TOOLS, [])
  const [selected, setSelected] = useState(() => {
    if (initialTools.length) {
      const ids = tools.filter((t) => initialTools.includes(t.label)).map((t) => t.id)
      return new Set(ids.length ? ids : ['estufa', 'microondas'])
    }
    return new Set(['estufa', 'microondas'])
  })
  const [custom, setCustom] = useState(() => {
    const known = new Set(tools.map((t) => t.label))
    return initialTools.filter((t) => !known.has(t)).join(', ')
  })
  const [error, setError] = useState('')

  function toggle(id) {
    setError('')
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function submit(e) {
    e.preventDefault()
    const extras = custom
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .map((label) => ({ id: `custom-${label}`, label }))

    const chosen = tools.filter((t) => selected.has(t.id)).concat(extras)
    if (!chosen.length) {
      setError('Elige al menos una herramienta.')
      return
    }
    onComplete(chosen.map((t) => t.label))
  }

  return (
    <section className="panel panel--onboard panel--lite">
      <h1 className="display display--md">¿Con qué cocinas?</h1>
      <p className="lede">Se guarda en este dispositivo.</p>

      <form className="stack" onSubmit={submit}>
        <div className="chip-grid" role="group" aria-label="Herramientas de cocina">
          {tools.map((tool) => {
            const active = selected.has(tool.id)
            return (
              <button
                key={tool.id}
                type="button"
                className={`chip ${active ? 'chip--on' : ''}`}
                onClick={() => toggle(tool.id)}
                aria-pressed={active}
              >
                {tool.label}
              </button>
            )
          })}
        </div>

        <label className="field">
          <span>Otras (opcional)</span>
          <input
            value={custom}
            onChange={(e) => {
              setCustom(e.target.value)
              setError('')
            }}
            placeholder="vaporera, molcajete…"
          />
        </label>

        {error ? <p className="field__error">{error}</p> : null}

        <button type="submit" className="btn btn--primary">
          Continuar
        </button>
      </form>
    </section>
  )
}
