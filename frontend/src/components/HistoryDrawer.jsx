import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'

export default function HistoryDrawer({ open, items, onClose, onOpenRecipe }) {
  const [mounted, setMounted] = useState(false)
  const panelRef = useRef(null)
  const backdropRef = useRef(null)
  const animRef = useRef(null)

  useEffect(() => {
    if (open) setMounted(true)
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  useLayoutEffect(() => {
    if (!mounted) return undefined

    const panel = panelRef.current
    const backdrop = backdropRef.current
    if (!panel || !backdrop) return undefined

    animRef.current?.kill()

    if (open) {
      gsap.set(backdrop, { autoAlpha: 0 })
      gsap.set(panel, { xPercent: 100 })
      animRef.current = gsap
        .timeline()
        .to(backdrop, { autoAlpha: 1, duration: 0.28, ease: 'power2.out' }, 0)
        .to(panel, { xPercent: 0, duration: 0.45, ease: 'power3.out' }, 0)
    } else {
      animRef.current = gsap
        .timeline({
          onComplete: () => setMounted(false),
        })
        .to(backdrop, { autoAlpha: 0, duration: 0.25, ease: 'power2.in' }, 0)
        .to(panel, { xPercent: 100, duration: 0.35, ease: 'power3.in' }, 0)
    }

    return () => animRef.current?.kill()
  }, [mounted, open])

  if (!mounted) return null

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Historial">
      <button
        type="button"
        className="drawer__backdrop"
        ref={backdropRef}
        aria-label="Cerrar"
        onClick={onClose}
      />
      <aside className="drawer__panel" ref={panelRef}>
        <header className="drawer__head">
          <h2>Historial</h2>
          <button type="button" className="btn btn--soft" onClick={onClose}>
            Cerrar
          </button>
        </header>
        <ul className="history-list">
          {items.length === 0 && <li className="empty">Todavía no hay actividad.</li>}
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="history-item"
                onClick={() => onOpenRecipe?.(item.recipe)}
              >
                <strong>{item.label}</strong>
                <span>{new Date(item.at).toLocaleString('es-MX')}</span>
                {item.recipe?.title && <em>{item.recipe.title}</em>}
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
