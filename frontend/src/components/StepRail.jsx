import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'

const STEPS = [
  { id: 'onboarding', label: 'Cocina', n: 1 },
  { id: 'compose', label: 'Refri', n: 2 },
  { id: 'results', label: 'Ideas', n: 3 },
]

export default function StepRail({ current }) {
  const currentIndex = STEPS.findIndex((s) => s.id === current)
  const railRef = useRef(null)

  useLayoutEffect(() => {
    const rail = railRef.current
    if (!rail) return undefined
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) return undefined

    const currentDot = rail.querySelector('.step-rail__item--current .step-rail__dot')
    if (!currentDot) return undefined

    const tween = gsap.fromTo(
      currentDot,
      { scale: 0.82 },
      { scale: 1, duration: 0.4, ease: 'back.out(1.8)' },
    )
    return () => tween.kill()
  }, [current])

  return (
    <nav className="step-rail step-rail--slim" aria-label="Progreso" ref={railRef}>
      <ol className="step-rail__list">
        {STEPS.map((step, index) => {
          const state =
            index < currentIndex ? 'done' : index === currentIndex ? 'current' : 'todo'
          return (
            <li key={step.id} className={`step-rail__item step-rail__item--${state}`}>
              <span className="step-rail__dot" aria-hidden="true">
                {state === 'done' ? '✓' : step.n}
              </span>
              <span className="step-rail__label">{step.label}</span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
