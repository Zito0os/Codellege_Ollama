import { useEffect, useRef } from 'react'

export default function RecipeDetail({ recipe, onClose, onSave, onUse, saved, used }) {
  const closeRef = useRef(null)
  const sheetRef = useRef(null)

  useEffect(() => {
    if (!recipe) return undefined

    const previous = document.activeElement
    closeRef.current?.focus()
    document.body.style.overflow = 'hidden'

    function onKey(e) {
      if (e.key === 'Escape') onClose()
      if (e.key !== 'Tab' || !sheetRef.current) return
      const focusables = sheetRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      )
      const list = [...focusables]
      if (!list.length) return
      const first = list[0]
      const last = list[list.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      if (previous instanceof HTMLElement) previous.focus()
    }
  }, [recipe, onClose])

  if (!recipe) return null

  return (
    <div className="modal modal--open" role="dialog" aria-modal="true" aria-label={recipe.title}>
      <button type="button" className="modal__backdrop" aria-label="Cerrar" onClick={onClose} />
      <div className="modal__sheet" ref={sheetRef}>
        <button type="button" className="modal__close" ref={closeRef} onClick={onClose}>
          Cerrar
        </button>
        <div className="modal__copy">
          <p className="eyebrow">{recipe.cuisine}</p>
          <h2 className="display display--sm">{recipe.title}</h2>
          <div className="meta">
            <span>{recipe.time}</span>
            <span>{recipe.difficulty}</span>
          </div>

          <h3>Ingredientes</h3>
          <ul className="detail-ings">
            {recipe.ingredients.map((ing) => (
              <li key={ing.name}>
                <span>{ing.name}</span>
                <span>{ing.amount}</span>
              </li>
            ))}
          </ul>

          <h3>Pasos</h3>
          <ol className="steps">
            {recipe.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>

          <div className="modal__actions">
            <button type="button" className="btn btn--soft" onClick={() => onSave(recipe)}>
              {saved ? 'Guardada' : 'Guardar'}
            </button>
            <button type="button" className="btn btn--soft btn--solid" onClick={() => onUse(recipe)} disabled={used}>
              {used ? 'Usada' : 'Usar esta'}
            </button>
          </div>
        </div>

        <figure className="modal__photo">
          <img src={recipe.image} alt={`Platillo: ${recipe.title}`} width="800" height="1000" />
          <figcaption>Referencia visual del platillo</figcaption>
        </figure>
      </div>
    </div>
  )
}
