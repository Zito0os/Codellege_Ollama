import { useEffect, useState } from 'react'

const messages = [
  'Revisando lo que tienes en el refri…',
  'Combinando sabores y antojos…',
  'Buscando ideas que puedas preparar…',
  'Ya casi salen tus recetas…',
]

export default function AnimatedLoading({ mode = 'generate' }) {
  const [messageIndex, setMessageIndex] = useState(0)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % messages.length)
    }, 2600)

    return () => window.clearInterval(interval)
  }, [])

  return (
    <div className="recipe-loading">
      <div className="recipe-loading__card" aria-busy="true">
        <div className="recipe-loading__art" aria-hidden="true">
          <span className="recipe-loading__steam recipe-loading__steam--one" />
          <span className="recipe-loading__steam recipe-loading__steam--two" />
          <span className="recipe-loading__steam recipe-loading__steam--three" />
          <span className="recipe-loading__shadow" />
          <svg className="recipe-loading__pan" viewBox="0 0 120 92" fill="none">
            <path
              d="M86 49h23c4 0 7 3 7 7s-3 7-7 7H87"
              stroke="currentColor"
              strokeWidth="8"
              strokeLinecap="round"
            />
            <path
              d="M18 51c0-17 14-31 32-31h12c18 0 32 14 32 31v7c0 13-10 23-23 23H41C28 81 18 71 18 58v-7Z"
              fill="#FFB56E"
              stroke="#9A3412"
              strokeWidth="5"
            />
            <path d="M13 52h83" stroke="#9A3412" strokeWidth="6" strokeLinecap="round" />
            <g className="recipe-loading__ingredients">
              <circle cx="39" cy="43" r="5" fill="#16845B" />
              <circle cx="59" cy="34" r="5" fill="#E65F35" />
              <circle cx="76" cy="46" r="5" fill="#16845B" />
            </g>
            <path d="M48 82v6m26-6v6" stroke="#9A3412" strokeWidth="5" strokeLinecap="round" />
          </svg>
          <span className="recipe-loading__spark recipe-loading__spark--one" />
          <span className="recipe-loading__spark recipe-loading__spark--two" />
        </div>
        <p className="recipe-loading__eyebrow">10go hambre · cocina en progreso</p>
        <h2 className="recipe-loading__title">
          {mode === 'regenerate' ? 'Buscando nuevas combinaciones' : 'La IA está cocinando tus ideas'}
        </h2>
        <p className="recipe-loading__message" key={messageIndex} role="status" aria-live="polite" aria-atomic="true">
          {messages[messageIndex]}
        </p>
        <div className="recipe-loading__progress" aria-hidden="true">
          <span />
        </div>
      </div>
    </div>
  )
}
