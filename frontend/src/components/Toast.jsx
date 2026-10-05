import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'

export default function Toast({ message, onDone, raised = false }) {
  const [text, setText] = useState('')
  const elRef = useRef(null)
  const onDoneRef = useRef(onDone)
  const tweenRef = useRef(null)
  onDoneRef.current = onDone

  useEffect(() => {
    if (message) setText(message)
  }, [message])

  useLayoutEffect(() => {
    if (!text || !elRef.current) return undefined

    const el = elRef.current
    tweenRef.current?.kill()

    gsap.set(el, { xPercent: -50, autoAlpha: 0, y: 16, scale: 0.96, filter: 'blur(6px)' })
    const intro = gsap.to(el, {
      autoAlpha: 1,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      duration: 0.45,
      ease: 'power3.out',
    })

    const hideTimer = window.setTimeout(() => {
      tweenRef.current = gsap.to(el, {
        autoAlpha: 0,
        y: 12,
        scale: 0.98,
        filter: 'blur(5px)',
        duration: 0.38,
        ease: 'power2.in',
        onComplete: () => {
          setText('')
          onDoneRef.current()
        },
      })
    }, 2500)

    return () => {
      intro.kill()
      window.clearTimeout(hideTimer)
      tweenRef.current?.kill()
    }
  }, [text])

  if (!text) return null

  return (
    <div
      className={`toast ${raised ? 'toast--raised' : ''}`}
      ref={elRef}
      role="status"
      aria-live="polite"
    >
      {text}
    </div>
  )
}
