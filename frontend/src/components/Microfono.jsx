import { useEffect } from 'react'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

export default function Microfono() {
  const { transcript, listening, browserSupportsSpeechRecognition, resetTranscript } =
    useSpeechRecognition()

  useEffect(() => () => SpeechRecognition.stopListening(), [])

  function iniciar(event) {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    resetTranscript()
    SpeechRecognition.startListening({ language: 'es-MX', continuous: true })
  }

  function detener() {
    if (listening) SpeechRecognition.stopListening()
  }

  return (
    <div className="voice-input" aria-live="polite">
      <button
        type="button"
        className={`voice-input__button ${listening ? 'voice-input__button--listening' : ''}`}
        onPointerDown={iniciar}
        onPointerUp={detener}
        onPointerCancel={detener}
        disabled={!browserSupportsSpeechRecognition}
        aria-label={listening ? 'Escuchando' : 'Mantén presionado para hablar'}
        aria-pressed={listening}
        title={
          browserSupportsSpeechRecognition
            ? 'Mantén presionado para hablar'
            : 'Tu navegador no soporta reconocimiento de voz'
        }
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
        </svg>
      </button>
      <p className="voice-input__transcript">
        {browserSupportsSpeechRecognition
          ? transcript || (listening ? 'Escuchando…' : 'Mantén presionado el micrófono y habla')
          : 'Tu navegador no soporta reconocimiento de voz.'}
      </p>
    </div>
  )
}