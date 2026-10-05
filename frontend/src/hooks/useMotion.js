import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useAmbientMotion(rootRef) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return undefined

    const mm = gsap.matchMedia()

    mm.add('(prefers-reduced-motion: no-preference)', () => {
      const shapes = root.querySelectorAll('[data-float]')
      shapes.forEach((el, i) => {
        gsap.to(el, {
          y: i % 2 === 0 ? -18 : 20,
          rotation: i % 2 === 0 ? 8 : -10,
          duration: 3.5 + i * 0.4,
          ease: 'sine.inOut',
          yoyo: true,
          repeat: -1,
        })
        gsap.to(el, {
          yPercent: i % 2 === 0 ? -10 : 14,
          ease: 'none',
          scrollTrigger: {
            trigger: root,
            start: 'top top',
            end: 'bottom bottom',
            scrub: 1.1,
          },
        })
      })
    })

    return () => mm.revert()
  }, [rootRef])
}

export function useReveal(deps = []) {
  const ref = useRef(null)

  useEffect(() => {
    const root = ref.current
    if (!root) return undefined

    const mm = gsap.matchMedia()
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      const items = root.querySelectorAll('[data-reveal]')
      gsap.from(items, {
        opacity: 0,
        y: 12,
        scale: 0.98,
        duration: 0.38,
        stagger: 0.05,
        ease: 'power1.out',
        clearProps: 'transform',
      })
    })

    return () => mm.revert()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}
