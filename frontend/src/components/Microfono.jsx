import { useEffect, useRef, useState } from 'react'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

const KEYBOARD_PRESS = 'keyboard'

export default function Microfono() {
  const {
    transcript,
    listening,
    browserSupportsSpeechRecognition,
    isMicrophoneAvailable,
    resetTranscript,
  } = useSpeechRecognition()
  const activePressRef = useRef(null)
  const pendingStartRef = useRef(null)
  const [pressed, setPressed] = useState(false)
  const [startError, setStartError] = useState('')
  const isSecureContext = window.isSecureContext
  const unavailableMessage = !isSecureContext
    ? 'El reconocimiento de voz requiere que abras esta página mediante HTTPS.'
    : !browserSupportsSpeechRecognition
      ? 'Este navegador no es compatible con el reconocimiento de voz.'
      : isMicrophoneAvailable === false
        ? 'No se pudo acceder al micrófono. Revisa los permisos de este sitio en el navegador y vuelve a intentarlo.'
        : ''
  const statusMessage = unavailableMessage || startError || transcript

  useEffect(
    () => () => {
      activePressRef.current = null
      void SpeechRecognition.stopListening()
    },
    [],
  )

  function iniciar(pressId) {
    if (
      unavailableMessage ||
      activePressRef.current !== null ||
      pendingStartRef.current !== null
    ) {
      return
    }

    activePressRef.current = pressId
    setPressed(true)
    setStartError('')
    resetTranscript()
    const startTask = SpeechRecognition.startListening({
      language: 'es-MX',
      continuous: true,
    })
      .then(() => {
        if (activePressRef.current !== pressId) {
          return SpeechRecognition.stopListening()
        }
      })
      .catch(() => {
        if (activePressRef.current === pressId) {
          activePressRef.current = null
          setPressed(false)
        }
        setStartError('No se pudo iniciar el micrófono. Revisa los permisos del navegador.')
      })
      .finally(() => {
        if (pendingStartRef.current === startTask) {
          pendingStartRef.current = null
        }
      })
    pendingStartRef.current = startTask
  }

  function detener(pressId) {
    if (activePressRef.current !== pressId) return
    activePressRef.current = null
    setPressed(false)
    if (pendingStartRef.current === null) {
      void SpeechRecognition.stopListening()
    }
  }

  function iniciarPointer(event) {
    if (!event.isPrimary || (event.pointerType === 'mouse' && event.button !== 0)) return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    iniciar(event.pointerId)
  }

  function detenerPointer(event) {
    detener(event.pointerId)
  }

  function iniciarTeclado(event) {
    if ((event.key !== ' ' && event.key !== 'Enter') || event.repeat) return
    event.preventDefault()
    iniciar(KEYBOARD_PRESS)
  }

  function detenerTeclado(event) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      detener(KEYBOARD_PRESS)
    }
  }

  return (
    <div className="voice-input">
      <button
        type="button"
        className={`voice-input__button ${pressed || listening ? 'voice-input__button--listening' : ''}`}
        onPointerDown={iniciarPointer}
        onPointerUp={detenerPointer}
        onPointerCancel={detenerPointer}
        onLostPointerCapture={detenerPointer}
        onKeyDown={iniciarTeclado}
        onKeyUp={detenerTeclado}
        onBlur={() => detener(KEYBOARD_PRESS)}
        disabled={Boolean(unavailableMessage)}
        aria-label="Mantén presionado para hablar"
        aria-pressed={pressed || listening}
        title={unavailableMessage || 'Mantén presionado para hablar'}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
        </svg>
      </button>
      {statusMessage && (
        <p className="voice-input__transcript" aria-live="polite">
          {statusMessage}
        </p>
      )}
    </div>
  )
}