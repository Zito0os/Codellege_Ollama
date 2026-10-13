import { useMemo, useState } from 'react'
import { DEFAULT_TOOLS } from '../data/tools'

const toolIcons = {
  estufa: (
    <>
      <rect x="5" y="7" width="30" height="25" rx="3" />
      <circle cx="13" cy="15" r="3" />
      <circle cx="27" cy="15" r="3" />
      <circle cx="13" cy="25" r="3" />
      <circle cx="27" cy="25" r="3" />
    </>
  ),
  horno: (
    <>
      <rect x="6" y="6" width="28" height="28" rx="3" />
      <path d="M11 12h18M11 17h18v12H11z" />
      <circle cx="13" cy="9" r=".7" />
      <circle cx="20" cy="9" r=".7" />
      <circle cx="27" cy="9" r=".7" />
    </>
  ),
  microondas: (
    <>
      <rect x="4" y="10" width="32" height="21" rx="3" />
      <rect x="8" y="14" width="19" height="13" rx="1.5" />
      <circle cx="32" cy="16" r="1" />
      <circle cx="32" cy="22" r="1" />
      <path d="M11 17h13M11 20h10" />
    </>
  ),
  licuadora: (
    <>
      <path d="M12 6h16l-2 19H14L12 6zM16 25v5M24 25v5M11 33h18" />
      <path d="M15 12h10M17 16h6" />
    </>
  ),
  procesador: (
    <>
      <path d="M10 14h20l-2 12H12l-2-12zM13 14V9h14v5M17 9V6h6v3" />
      <path d="M16 26v5h8v-5M14 34h12" />
      <path d="M20 15v7M17 19h6" />
    </>
  ),
  airfryer: (
    <>
      <rect x="8" y="5" width="24" height="29" rx="6" />
      <path d="M12 17h16v10H12zM17 11h6M18 30h4" />
      <circle cx="20" cy="14" r="1" />
    </>
  ),
  olla_presion: (
    <>
      <path d="M10 15h20l-2 16H12l-2-16zM8 18H5v8h5M32 18h3v8h-5" />
      <path d="M8 13h24M15 9h10M18 6h4M16 20v8M24 20v8" />
    </>
  ),
  batidora: (
    <>
      <path d="M10 7h15l5 5-5 5H14v9h13M14 26h13l-2 7H14z" />
      <path d="M17 17v5M20 17v5M23 17v5M11 33h16" />
    </>
  ),
  toaster: (
    <>
      <path d="M8 17a5 5 0 0 1 5-5h14a5 5 0 0 1 5 5v14H8V17z" />
      <path d="M14 12V6M25 12V6M13 21h14M13 25h14M20 31v4" />
    </>
  ),
  grill: (
    <>
      <path d="M7 14h26l-3 10H10L7 14zM11 24l-3 10M29 24l3 10" />
      <path d="M11 17h18M12 21h16M14 14v10M20 14v10M26 14v10" />
      <path d="M14 10c-2-2 2-3 0-5M21 10c-2-2 2-3 0-5M28 10c-2-2 2-3 0-5" />
    </>
  ),
}

function ToolIcon({ id }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <g
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {toolIcons[id] || toolIcons.estufa}
      </g>
    </svg>
  )
}

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
          {tools.map((tool, index) => {
            const active = selected.has(tool.id)
            return (
              <button
                key={tool.id}
                type="button"
                className={`chip ${active ? 'chip--on' : ''}`}
                onClick={() => toggle(tool.id)}
                aria-pressed={active}
              >
                <span className="chip__meta" aria-hidden="true">
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <svg className="chip__check" viewBox="0 0 20 20" fill="none">
                    <path
                      d="m4 10 4 4 8-8"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="chip__icon">
                  <ToolIcon id={tool.id} />
                </span>
                <span className="chip__label">{tool.label}</span>
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
