import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'

const ORDER = {
  onboarding: 0,
  compose: 1,
  results: 2,
}

export default function StepStage({ step, direction = 1, children }) {
  const ref = useRef(null)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return undefined

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      gsap.set(el, { clearProps: 'all' })
      return undefined
    }

    const fromX = direction >= 0 ? 28 : -28
    const tween = gsap.fromTo(
      el,
      {
        autoAlpha: 0,
        x: fromX,
        y: 10,
        filter: 'blur(8px)',
      },
      {
        autoAlpha: 1,
        x: 0,
        y: 0,
        filter: 'blur(0px)',
        duration: 0.48,
        ease: 'power3.out',
        clearProps: 'filter',
      },
    )

    return () => tween.kill()
  }, [step, direction])

  return (
    <div className="step-stage" ref={ref}>
      {children}
    </div>
  )
}

export function stepDirection(from, to) {
  return (ORDER[to] ?? 0) >= (ORDER[from] ?? 0) ? 1 : -1
}
