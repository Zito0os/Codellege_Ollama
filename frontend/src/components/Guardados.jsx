import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import RecipeCard from './Results'
import { getSavedRecipes, saveRecipe, unsaveRecipe } from '../utils/storage'

export default function Guardados({ children }) {
  const [recipes, setRecipes] = useState(() => getSavedRecipes())
  const [open, setOpen] = useState(false)

  const toggleSaved = useCallback((recipe) => {
    const exists = recipes.some((savedRecipe) => savedRecipe.id === recipe.id)
    setRecipes(exists ? unsaveRecipe(recipe.id) : saveRecipe(recipe))
    return !exists
  }, [recipes])

  return children({ recipes, open, setOpen, toggleSaved })
}

export function GuardadosTrigger({ count, open, onOpen }) {
  return (
    <button
      type="button"
      className="btn btn--soft topbar__saved"
      onClick={onOpen}
      aria-label={`Ver recetas guardadas: ${count}`}
      aria-haspopup="dialog"
      aria-expanded={open}
    >
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M5 3.5h10v13l-5-3.2-5 3.2v-13z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      </svg>
    
    </button>
  )
}

export function GuardadosDrawer({ open, recipes, savedIds, usedId, onClose, onOpenRecipe, onSave, onUse }) {
  const closeRef = useRef(null)
  const panelRef = useRef(null)
  const backdropRef = useRef(null)
  const animRef = useRef(null)
  const hasOpened = useRef(false)

  useLayoutEffect(() => {
    const panel = panelRef.current
    const backdrop = backdropRef.current
    if (!panel || !backdrop) return undefined

    animRef.current?.kill()

    if (open) {
      hasOpened.current = true
      gsap.set(backdrop, { autoAlpha: 0 })
      gsap.set(panel, { xPercent: 100 })
      animRef.current = gsap
        .timeline()
        .to(backdrop, { autoAlpha: 1, duration: 0.28, ease: 'power2.out' }, 0)
        .to(panel, { xPercent: 0, duration: 0.45, ease: 'power3.out' }, 0)
    } else if (!hasOpened.current) {
      gsap.set(backdrop, { autoAlpha: 0 })
      gsap.set(panel, { xPercent: 100 })
      return undefined
    } else {
      animRef.current = gsap
        .timeline()
        .to(backdrop, { autoAlpha: 0, duration: 0.25, ease: 'power2.in' }, 0)
        .to(panel, { xPercent: 100, duration: 0.35, ease: 'power3.in' }, 0)
    }

    return () => animRef.current?.kill()
  }, [open])

  useEffect(() => {
    if (!open) return undefined

    const previous = document.activeElement
    closeRef.current?.focus()
    document.body.style.overflow = 'hidden'

    function onKeyDown(event) {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab' || !panelRef.current) return

      const focusable = panelRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      )
      const items = [...focusable]
      if (!items.length) return

      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
      if (previous instanceof HTMLElement) previous.focus()
    }
  }, [onClose, open])

  return (
    <div
      className="drawer"
      role="dialog"
      aria-modal="true"
      aria-label="Mis recetas guardadas"
      aria-hidden={!open}
      inert={!open}
    >
      <button
        type="button"
        className="drawer__backdrop"
        ref={backdropRef}
        aria-label="Cerrar recetas guardadas"
        onClick={onClose}
      />
      <aside className="drawer__panel saved-recipes-drawer__panel" ref={panelRef}>
        <header className="drawer__head">
          <h2>Mis recetas</h2>
          <button type="button" className="btn btn--soft" ref={closeRef} onClick={onClose}>
            Cerrar
          </button>
        </header>
        {recipes.length ? (
          <div className="saved-recipes-list">
            {recipes.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                saved={savedIds.has(recipe.id)}
                used={usedId === recipe.id}
                onOpen={onOpenRecipe}
                onSave={onSave}
                onUse={onUse}
              />
            ))}
          </div>
        ) : (
          <p className="saved-recipes-empty">Todavía no hay recetas guardadas.</p>
        )}
      </aside>
    </div>
  )
}
